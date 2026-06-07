-- Ejecutar en Supabase Dashboard -> SQL Editor

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    nombre      NVARCHAR(50) NOT NULL UNIQUE,
    descripcion NVARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usuarios (
    id            SERIAL PRIMARY KEY,
    nombre        NVARCHAR(100) NOT NULL,
    email         VARCHAR(150)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    rol_id        INT           NOT NULL REFERENCES roles(id),
    activo        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ   DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   DEFAULT NOW()
);

-- Deshabilitar RLS para operaciones de backend con clave anon
ALTER TABLE roles    DISABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios DISABLE ROW LEVEL SECURITY;

-- Seed de roles base
INSERT INTO roles (nombre, descripcion) VALUES
    ('USUARIO', 'Usuario estándar de la plataforma'),
    ('ADMINISTRADOR', 'Acceso total al sistema')
ON CONFLICT (nombre) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_usuarios_rol_id ON usuarios(rol_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios(activo);
