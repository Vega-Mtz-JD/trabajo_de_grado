-- Roles de la instancia PostgreSQL (nivel de clúster; idempotente). Ver ADR-008.
-- Se ejecuta una vez por instancia, como superusuario.

DO $$
BEGIN
    -- Dueño de esquemas, tablas y funciones SECURITY DEFINER. Nadie inicia sesión con él.
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vs_propietario') THEN
        CREATE ROLE vs_propietario NOLOGIN;
    END IF;
    -- Aplicación: solo los permisos mínimos y las funciones de negocio (emitir voto, mezclar).
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vs_app') THEN
        CREATE ROLE vs_app LOGIN;
    END IF;
    -- Auditor: solo lectura (sin plantillas biométricas).
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vs_auditor') THEN
        CREATE ROLE vs_auditor LOGIN;
    END IF;
    -- Administrador de BD: respaldos y mantenimiento; no participa en la votación.
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vs_admin_bd') THEN
        CREATE ROLE vs_admin_bd LOGIN;
    END IF;
END
$$;

-- El administrador de BD puede asumir el rol propietario (SET ROLE) solo para aplicar migraciones,
-- pero NO hereda sus privilegios en el uso normal (PostgreSQL 16+). ADR-011.
GRANT vs_propietario TO vs_admin_bd WITH INHERIT FALSE, SET TRUE;
