-- Esquema de la base de datos de VOTO SEGURO (PostgreSQL 17). Ver ADR-004 y ADR-008.
-- Se ejecuta como superusuario sobre una base de datos vacía, después de roles.sql.
--
-- Principios:
--   * Mínimo privilegio: vs_app no tiene UPDATE/DELETE sobre votos ni bitácora; emite votos
--     solo mediante la función urna.emitir_voto().
--   * Solo inserción: votos, bitácora, actas y checkpoints no se pueden modificar ni borrar.
--   * Secreto del voto: la urna no guarda hora ni orden; urna.mezclar() borra el orden físico
--     y el xmin de las filas (ADR-008).

CREATE SCHEMA eleccion   AUTHORIZATION vs_propietario;
CREATE SCHEMA padron     AUTHORIZATION vs_propietario;
CREATE SCHEMA urna       AUTHORIZATION vs_propietario;
CREATE SCHEMA auditoria  AUTHORIZATION vs_propietario;
CREATE SCHEMA blockchain AUTHORIZATION vs_propietario;

SET ROLE vs_propietario;

-- ===================================================================== Funciones comunes

-- Bloquea UPDATE, DELETE y TRUNCATE en tablas de solo inserción. La única excepción es el
-- TRUNCATE de la urna dentro de urna.mezclar() (que solo puede ejecutar el propietario).
CREATE FUNCTION auditoria.prohibir_modificacion() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' AND TG_TABLE_SCHEMA = 'urna'
       AND current_setting('votoseguro.mezcla', true) = 'on' THEN
        RETURN NULL;
    END IF;
    RAISE EXCEPTION 'operación % prohibida en %.%: tabla de solo inserción',
        TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'VS100';
END
$$;

-- ===================================================================== Elección

-- Una fila = una MESA de una elección (ADR-009). Varias urnas comparten eleccion_global y la
-- definición (opciones, sal del padrón), pero cada mesa tiene su propia clave y custodios.
CREATE TABLE eleccion.eleccion (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    eleccion_global       uuid NOT NULL,
    mesa                  text NOT NULL CHECK (mesa ~ '^[A-Z0-9-]{1,10}$'),
    nombre                text NOT NULL CHECK (length(nombre) BETWEEN 3 AND 200),
    sal_padron            text NOT NULL CHECK (sal_padron ~ '^[0-9a-f]{32}$'),
    hash_configuracion    text NOT NULL CHECK (hash_configuracion ~ '^[0-9a-f]{64}$'),
    definicion            jsonb NOT NULL,      -- definición completa (opciones, mesas, umbral…)
    estado                text NOT NULL DEFAULT 'CONFIGURACION'
                          CHECK (estado IN ('CONFIGURACION', 'EMPADRONAMIENTO', 'LISTA',
                                            'ABIERTA', 'CERRADA', 'ESCRUTADA', 'EXPORTADA')),
    clave_publica         bytea NOT NULL,
    clave_privada_cifrada bytea NOT NULL,
    umbral                smallint NOT NULL,
    partes                smallint NOT NULL,
    checkpoint_cada       smallint NOT NULL DEFAULT 10 CHECK (checkpoint_cada >= 10),
    creada_en             timestamptz NOT NULL DEFAULT now(),
    CHECK (umbral >= 2 AND umbral <= partes),
    UNIQUE (eleccion_global, mesa)
);

-- Solo se permiten las transiciones de la máquina de estados (propuesta §10.2) y los
-- datos criptográficos son inmutables una vez creada la elección.
CREATE FUNCTION eleccion.validar_cambio() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.id, NEW.eleccion_global, NEW.mesa, NEW.sal_padron, NEW.hash_configuracion, NEW.definicion, NEW.clave_publica,
        NEW.clave_privada_cifrada, NEW.umbral, NEW.partes, NEW.creada_en)
       IS DISTINCT FROM
       (OLD.id, OLD.eleccion_global, OLD.mesa, OLD.sal_padron, OLD.hash_configuracion, OLD.definicion, OLD.clave_publica,
        OLD.clave_privada_cifrada, OLD.umbral, OLD.partes, OLD.creada_en) THEN
        RAISE EXCEPTION 'los datos criptográficos de la elección son inmutables' USING ERRCODE = 'VS100';
    END IF;
    IF NEW.estado IS DISTINCT FROM OLD.estado AND (OLD.estado, NEW.estado) NOT IN (
        ('CONFIGURACION', 'EMPADRONAMIENTO'), ('EMPADRONAMIENTO', 'LISTA'), ('LISTA', 'ABIERTA'),
        ('ABIERTA', 'CERRADA'), ('CERRADA', 'ESCRUTADA'), ('ESCRUTADA', 'EXPORTADA')) THEN
        RAISE EXCEPTION 'transición de estado inválida: % → %', OLD.estado, NEW.estado
            USING ERRCODE = 'VS003';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER eleccion_validar_cambio BEFORE UPDATE ON eleccion.eleccion
    FOR EACH ROW EXECUTE FUNCTION eleccion.validar_cambio();
CREATE TRIGGER eleccion_sin_borrado BEFORE DELETE ON eleccion.eleccion
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();

CREATE TABLE eleccion.opcion (
    id          serial PRIMARY KEY,
    eleccion_id uuid NOT NULL REFERENCES eleccion.eleccion,
    codigo      text NOT NULL CHECK (codigo ~ '^[A-Z0-9_-]{1,20}$'),
    nombre      text NOT NULL,
    frente      text,
    orden       smallint NOT NULL,
    tipo        text NOT NULL CHECK (tipo IN ('CANDIDATO', 'BLANCO', 'NULO')),
    UNIQUE (eleccion_id, codigo),
    UNIQUE (eleccion_id, orden)
);

CREATE TABLE eleccion.checkpoint (
    eleccion_id uuid NOT NULL REFERENCES eleccion.eleccion,
    seq         integer NOT NULL CHECK (seq >= 1),
    conteo      integer NOT NULL CHECK (conteo >= 0),
    raiz_merkle text NOT NULL CHECK (raiz_merkle ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (eleccion_id, seq)
);

CREATE TABLE eleccion.acta (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    eleccion_id uuid NOT NULL REFERENCES eleccion.eleccion,
    tipo        text NOT NULL CHECK (tipo IN ('ZERESIMA', 'CIERRE', 'ESCRUTINIO')),
    contenido   jsonb NOT NULL,
    hash        text NOT NULL CHECK (hash ~ '^[0-9a-f]{64}$'),
    firma       bytea NOT NULL,
    UNIQUE (eleccion_id, tipo)
);

CREATE TABLE eleccion.usuario (
    nombre        text PRIMARY KEY CHECK (nombre ~ '^[a-z][a-z0-9_.]{2,30}$'),
    rol           text NOT NULL CHECK (rol IN ('ADMIN', 'OPERADOR', 'AUDITOR')),
    hash_password text NOT NULL,
    clave_publica bytea,
    activo        boolean NOT NULL DEFAULT true
);

-- ===================================================================== Padrón

CREATE TABLE padron.votante (
    eleccion_id       uuid NOT NULL REFERENCES eleccion.eleccion,
    ci                text NOT NULL CHECK (ci ~ '^[0-9]{5,10}(-[0-9A-Z]{1,3})?$'),
    nombres           text NOT NULL,
    apellidos         text NOT NULL,
    plantilla_cifrada bytea,
    foto_cifrada      bytea,                            -- foto de registro (ADR-009)
    habilitado        boolean NOT NULL DEFAULT true,
    ya_voto           boolean NOT NULL DEFAULT false,   -- sin hora de voto (ADR-004)
    PRIMARY KEY (eleccion_id, ci)
);

-- ya_voto solo pasa de false a true y solo dentro de urna.emitir_voto() (que se ejecuta
-- como vs_propietario). El padrón solo se modifica antes de la apertura.
CREATE FUNCTION padron.validar_votante() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_estado text;
BEGIN
    SELECT estado INTO v_estado FROM eleccion.eleccion WHERE id = NEW.eleccion_id;
    IF TG_OP = 'INSERT' THEN
        IF NEW.ya_voto THEN
            RAISE EXCEPTION 'un votante no puede registrarse como que ya votó' USING ERRCODE = 'VS100';
        END IF;
        IF v_estado NOT IN ('CONFIGURACION', 'EMPADRONAMIENTO') THEN
            RAISE EXCEPTION 'el padrón está cerrado (estado %)', v_estado USING ERRCODE = 'VS003';
        END IF;
        RETURN NEW;
    END IF;
    IF (NEW.eleccion_id, NEW.ci) IS DISTINCT FROM (OLD.eleccion_id, OLD.ci) THEN
        RAISE EXCEPTION 'no se puede cambiar el CI ni la elección de un votante' USING ERRCODE = 'VS100';
    END IF;
    IF NEW.ya_voto IS DISTINCT FROM OLD.ya_voto THEN
        IF OLD.ya_voto OR current_user <> 'vs_propietario' THEN
            RAISE EXCEPTION 'ya_voto solo cambia al emitir el voto' USING ERRCODE = 'VS100';
        END IF;
    ELSIF v_estado NOT IN ('CONFIGURACION', 'EMPADRONAMIENTO') THEN
        RAISE EXCEPTION 'el padrón está cerrado (estado %)', v_estado USING ERRCODE = 'VS003';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER votante_validar BEFORE INSERT OR UPDATE ON padron.votante
    FOR EACH ROW EXECUTE FUNCTION padron.validar_votante();
CREATE TRIGGER votante_sin_borrado BEFORE DELETE ON padron.votante
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();

-- Presencia: el votante se identificó en la jornada (foto de presencia, método). Es información
-- de la mesa de identificación (como firmar la lista de votantes); NO se vincula al voto.
CREATE TABLE padron.presencia (
    eleccion_id  uuid NOT NULL,
    ci           text NOT NULL,
    momento      timestamptz NOT NULL DEFAULT now(),
    metodo       text NOT NULL CHECK (metodo IN ('HUELLA', 'EXCEPCION')),
    foto_cifrada bytea,
    PRIMARY KEY (eleccion_id, ci),
    FOREIGN KEY (eleccion_id, ci) REFERENCES padron.votante (eleccion_id, ci)
);

CREATE FUNCTION padron.validar_presencia() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT estado FROM eleccion.eleccion WHERE id = NEW.eleccion_id) IS DISTINCT FROM 'ABIERTA' THEN
        RAISE EXCEPTION 'la elección no está abierta' USING ERRCODE = 'VS002';
    END IF;
    IF NOT EXISTS (SELECT FROM padron.votante
                    WHERE eleccion_id = NEW.eleccion_id AND ci = NEW.ci AND habilitado) THEN
        RAISE EXCEPTION 'votante no habilitado' USING ERRCODE = 'VS001';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER presencia_validar BEFORE INSERT ON padron.presencia
    FOR EACH ROW EXECUTE FUNCTION padron.validar_presencia();
CREATE TRIGGER presencia_solo_insercion BEFORE UPDATE OR DELETE ON padron.presencia
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();

-- ===================================================================== Urna

-- Sin fecha, sin hora y sin columna de orden. La clave primaria es aleatoria.
CREATE TABLE urna.voto (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    eleccion_id  uuid NOT NULL REFERENCES eleccion.eleccion,
    voto_cifrado bytea NOT NULL,
    hash_voto    text NOT NULL UNIQUE CHECK (hash_voto ~ '^[0-9a-f]{64}$')
);

CREATE FUNCTION urna.validar_insercion() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF current_setting('votoseguro.mezcla', true) = 'on' THEN
        RETURN NEW;   -- reinserción durante la mezcla
    END IF;
    IF (SELECT estado FROM eleccion.eleccion WHERE id = NEW.eleccion_id) IS DISTINCT FROM 'ABIERTA' THEN
        RAISE EXCEPTION 'la elección no está abierta' USING ERRCODE = 'VS002';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER voto_validar BEFORE INSERT ON urna.voto
    FOR EACH ROW EXECUTE FUNCTION urna.validar_insercion();
CREATE TRIGGER voto_solo_insercion BEFORE UPDATE OR DELETE ON urna.voto
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();
CREATE TRIGGER voto_sin_truncate BEFORE TRUNCATE ON urna.voto
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria.prohibir_modificacion();

-- Emisión atómica: marca ya_voto e inserta el voto cifrado en la misma transacción.
-- Devuelve el total de votos de la elección (para decidir cuándo hacer checkpoint).
CREATE FUNCTION urna.emitir_voto(p_eleccion uuid, p_ci text, p_voto bytea, p_hash text)
RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    v_estado text;
    v_total  bigint;
BEGIN
    SELECT estado INTO v_estado FROM eleccion.eleccion WHERE id = p_eleccion FOR SHARE;
    IF v_estado IS DISTINCT FROM 'ABIERTA' THEN
        RAISE EXCEPTION 'la elección no está abierta' USING ERRCODE = 'VS002';
    END IF;
    UPDATE padron.votante SET ya_voto = true
     WHERE eleccion_id = p_eleccion AND ci = p_ci AND habilitado AND NOT ya_voto;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'votante no habilitado, inexistente o que ya votó' USING ERRCODE = 'VS001';
    END IF;
    INSERT INTO urna.voto (eleccion_id, voto_cifrado, hash_voto) VALUES (p_eleccion, p_voto, p_hash);
    SELECT count(*) INTO v_total FROM urna.voto WHERE eleccion_id = p_eleccion;
    RETURN v_total;
END
$$;

-- Huella del contenido de la urna: SHA-256 de los hashes de voto ordenados. Sirve para
-- comprobar que la mezcla no agregó, quitó ni alteró ningún voto.
CREATE FUNCTION urna.huella_urna() RETURNS TABLE (conteo bigint, huella text)
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $$
    SELECT count(*),
           encode(sha256(convert_to(coalesce(string_agg(hash_voto, ',' ORDER BY hash_voto), ''), 'UTF8')), 'hex')
      FROM urna.voto
$$;

-- Mezcla de la urna (ADR-008): reescribe todas las filas en orden aleatorio dentro de una
-- transacción. Después de la mezcla, todas las filas comparten el mismo xmin y su orden
-- físico es aleatorio, lo que borra el orden de emisión. Verifica que el contenido no cambió.
CREATE FUNCTION urna.mezclar() RETURNS TABLE (conteo bigint, huella text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    c_antes bigint; h_antes text;
    c_despues bigint; h_despues text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('urna.voto'));
    LOCK TABLE urna.voto IN ACCESS EXCLUSIVE MODE;
    SELECT * INTO c_antes, h_antes FROM urna.huella_urna();

    CREATE TEMP TABLE _mezcla ON COMMIT DROP AS SELECT * FROM urna.voto;
    PERFORM set_config('votoseguro.mezcla', 'on', true);
    TRUNCATE urna.voto;
    INSERT INTO urna.voto SELECT * FROM _mezcla ORDER BY gen_random_uuid();
    PERFORM set_config('votoseguro.mezcla', 'off', true);
    DROP TABLE _mezcla;

    SELECT * INTO c_despues, h_despues FROM urna.huella_urna();
    IF c_antes <> c_despues OR h_antes <> h_despues THEN
        RAISE EXCEPTION 'la mezcla alteró el contenido de la urna' USING ERRCODE = 'VS101';
    END IF;
    RETURN QUERY SELECT c_despues, h_despues;
END
$$;

-- ===================================================================== Auditoría

-- Bitácora encadenada: hash = SHA3-256(hash_anterior ‖ evento canónico), calculado por la
-- aplicación. La base de datos exige que cada entrada apunte al hash de la anterior.
CREATE TABLE auditoria.bitacora (
    seq           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    momento       timestamptz NOT NULL,
    actor         text NOT NULL,
    evento        text NOT NULL CHECK (evento ~ '^[A-Z][A-Z0-9_]{2,50}$'),
    detalle       jsonb NOT NULL DEFAULT '{}'::jsonb,
    hash_anterior text NOT NULL CHECK (hash_anterior ~ '^[0-9a-f]{64}$'),
    hash          text NOT NULL UNIQUE CHECK (hash ~ '^[0-9a-f]{64}$')
);

CREATE FUNCTION auditoria.validar_encadenamiento() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_ultimo text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('auditoria.bitacora'));
    SELECT hash INTO v_ultimo FROM auditoria.bitacora ORDER BY seq DESC LIMIT 1;
    IF NEW.hash_anterior IS DISTINCT FROM coalesce(v_ultimo, repeat('0', 64)) THEN
        RAISE EXCEPTION 'la entrada no está encadenada al último hash de la bitácora'
            USING ERRCODE = 'VS102';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER bitacora_encadenar BEFORE INSERT ON auditoria.bitacora
    FOR EACH ROW EXECUTE FUNCTION auditoria.validar_encadenamiento();
CREATE TRIGGER bitacora_solo_insercion BEFORE UPDATE OR DELETE ON auditoria.bitacora
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();
CREATE TRIGGER bitacora_sin_truncate BEFORE TRUNCATE ON auditoria.bitacora
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria.prohibir_modificacion();

CREATE TRIGGER acta_solo_insercion BEFORE UPDATE OR DELETE ON eleccion.acta
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();
CREATE TRIGGER checkpoint_solo_insercion BEFORE UPDATE OR DELETE ON eleccion.checkpoint
    FOR EACH ROW EXECUTE FUNCTION auditoria.prohibir_modificacion();

-- ===================================================================== Blockchain (outbox)

CREATE TABLE blockchain.outbox (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    funcion    text NOT NULL,
    argumentos jsonb NOT NULL,
    estado     text NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'ENVIADO', 'ERROR')),
    intentos   integer NOT NULL DEFAULT 0,
    tx_id      text
);

RESET ROLE;

-- ===================================================================== Privilegios

REVOKE ALL ON SCHEMA eleccion, padron, urna, auditoria, blockchain FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA eleccion, padron, urna, auditoria FROM PUBLIC;

GRANT USAGE ON SCHEMA eleccion, padron, urna, auditoria, blockchain TO vs_app, vs_auditor;

-- Aplicación
GRANT SELECT, INSERT ON eleccion.eleccion, eleccion.opcion, eleccion.checkpoint, eleccion.acta TO vs_app;
GRANT UPDATE (estado) ON eleccion.eleccion TO vs_app;
GRANT SELECT, INSERT ON eleccion.usuario TO vs_app;
GRANT UPDATE (hash_password, clave_publica, activo) ON eleccion.usuario TO vs_app;
GRANT USAGE ON SEQUENCE eleccion.opcion_id_seq TO vs_app;
GRANT SELECT, INSERT ON padron.votante TO vs_app;
GRANT UPDATE (nombres, apellidos, plantilla_cifrada, foto_cifrada, habilitado) ON padron.votante TO vs_app;
GRANT SELECT, INSERT ON padron.presencia TO vs_app;
GRANT SELECT ON urna.voto TO vs_app;                     -- sin INSERT directo: usa emitir_voto()
GRANT EXECUTE ON FUNCTION urna.emitir_voto(uuid, text, bytea, text), urna.mezclar(),
                          urna.huella_urna() TO vs_app;
GRANT SELECT, INSERT ON auditoria.bitacora TO vs_app;
GRANT SELECT, INSERT ON blockchain.outbox TO vs_app;
GRANT UPDATE (estado, intentos, tx_id) ON blockchain.outbox TO vs_app;

-- Auditor: solo lectura; del padrón no ve las plantillas biométricas.
GRANT SELECT ON ALL TABLES IN SCHEMA eleccion, urna, auditoria, blockchain TO vs_auditor;
REVOKE SELECT ON eleccion.usuario FROM vs_auditor;
GRANT SELECT (nombre, rol, clave_publica, activo) ON eleccion.usuario TO vs_auditor;
GRANT SELECT (eleccion_id, ci, nombres, apellidos, habilitado, ya_voto) ON padron.votante TO vs_auditor;
GRANT SELECT (eleccion_id, ci, momento, metodo) ON padron.presencia TO vs_auditor;
GRANT EXECUTE ON FUNCTION urna.huella_urna() TO vs_auditor;
