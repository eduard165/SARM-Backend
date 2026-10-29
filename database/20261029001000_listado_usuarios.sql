-- SARM 10: listado de usuarios para la administracion. Requiere 01-09.
-- Solo lectura. No modifica cuentas, membresias, roles ni politicas RLS.
BEGIN;
CREATE OR REPLACE FUNCTION public.sarm_listar_usuarios(
    p_actor uuid,
    p_busqueda text DEFAULT NULL,
    p_rol text DEFAULT NULL,
    p_negocio uuid DEFAULT NULL,
    p_estado text DEFAULT NULL,
    p_pagina integer DEFAULT 1,
    p_tamano integer DEFAULT 20
) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_rol text;
    v_negocio uuid;
    v_total_membresias integer;
    v_resultado jsonb;
BEGIN
    SELECT r.codigo INTO v_rol
    FROM public.usuarios u JOIN public.roles r ON r.id = u.rol_id
    WHERE u.id = p_actor AND NOT u.bloqueo_global;

    IF v_rol IS NULL OR v_rol NOT IN ('superadministrador', 'administrador') THEN
        RAISE EXCEPTION 'No tienes permiso para consultar usuarios' USING ERRCODE = '42501';
    END IF;
    IF p_pagina IS NULL OR p_pagina < 1 OR p_pagina > 1000000
       OR p_tamano IS NULL OR p_tamano NOT BETWEEN 1 AND 100
       OR char_length(coalesce(p_busqueda, '')) > 100
       OR (p_rol IS NOT NULL AND p_rol NOT IN ('superadministrador', 'administrador', 'usuario'))
       OR (p_estado IS NOT NULL AND p_estado NOT IN ('activo', 'suspendido')) THEN
        RAISE EXCEPTION 'Filtros o paginacion invalidos' USING ERRCODE = '22023';
    END IF;

    IF v_rol = 'administrador' THEN
        -- Cuenta exactamente una membresia, incluso cuando esta suspendida.
        SELECT count(*), (array_agg(un.negocio_id))[1]
        INTO v_total_membresias, v_negocio
        FROM public.usuario_negocios un WHERE un.usuario_id = p_actor;
        IF v_total_membresias <> 1 OR NOT EXISTS (
            SELECT 1 FROM public.usuario_negocios un
            JOIN public.negocios n ON n.id = un.negocio_id
            WHERE un.usuario_id = p_actor AND un.negocio_id = v_negocio
              AND un.estado_membresia = 'activo' AND n.estado_registro = 'activo'
        ) THEN
            RAISE EXCEPTION 'Administrador sin negocio unico activo' USING ERRCODE = '42501';
        END IF;
        IF (p_negocio IS NOT NULL AND p_negocio <> v_negocio)
           OR (p_rol IS NOT NULL AND p_rol <> 'usuario') THEN
            RAISE EXCEPTION 'Filtro fuera de tu alcance' USING ERRCODE = '42501';
        END IF;
    ELSE
        v_negocio := p_negocio;
    END IF;

    WITH visibles AS (
        SELECT u.id, u.nombre_usuario, u.nombre, u.apellido_paterno,
            u.apellido_materno, u.bloqueo_global, u.creado_en,
            r.codigo AS rol,
            concat_ws(' ', u.nombre, u.apellido_paterno, u.apellido_materno) AS nombre_completo,
            CASE
                WHEN u.bloqueo_global THEN 'suspendido'
                WHEN r.codigo = 'superadministrador' AND v_negocio IS NULL THEN 'activo'
                WHEN EXISTS (
                    SELECT 1 FROM public.usuario_negocios m
                    JOIN public.negocios n ON n.id = m.negocio_id
                    WHERE m.usuario_id = u.id AND m.estado_membresia = 'activo'
                      AND n.estado_registro = 'activo'
                      AND (v_negocio IS NULL OR m.negocio_id = v_negocio)
                ) THEN 'activo'
                ELSE 'suspendido'
            END AS estado
        FROM public.usuarios u JOIN public.roles r ON r.id = u.rol_id
        WHERE (v_rol = 'superadministrador' OR (r.codigo = 'usuario' AND u.id <> p_actor))
          AND (v_negocio IS NULL OR EXISTS (
              SELECT 1 FROM public.usuario_negocios m
              WHERE m.usuario_id = u.id AND m.negocio_id = v_negocio
          ))
          AND (p_rol IS NULL OR r.codigo = p_rol)
          -- Busqueda literal: %, comas o parentesis no pueden alterar filtros.
          AND (nullif(btrim(p_busqueda), '') IS NULL OR strpos(
              lower(concat_ws(' ', u.nombre_usuario, u.nombre, u.apellido_paterno, u.apellido_materno)),
              lower(btrim(p_busqueda))
          ) > 0)
    ), filtrados AS (
        SELECT * FROM visibles WHERE p_estado IS NULL OR estado = p_estado
    ), pagina AS (
        SELECT * FROM filtrados ORDER BY lower(nombre_usuario), id
        OFFSET ((p_pagina - 1)::bigint * p_tamano) LIMIT p_tamano
    ), elementos AS (
        SELECT p.*, coalesce((
            SELECT jsonb_agg(jsonb_build_object(
                'negocio_id', m.negocio_id,
                'nombre', n.nombre,
                'estado_membresia', m.estado_membresia,
                'estado_negocio', n.estado_registro
            ) ORDER BY lower(n.nombre), n.id)
            FROM public.usuario_negocios m JOIN public.negocios n ON n.id = m.negocio_id
            WHERE m.usuario_id = p.id
              -- El administrador no recibe informacion de otras membresias.
              AND (v_rol = 'superadministrador' OR m.negocio_id = v_negocio)
        ), '[]'::jsonb) AS negocios
        FROM pagina p
    )
    SELECT jsonb_build_object(
        'items', coalesce((SELECT jsonb_agg(to_jsonb(e) ORDER BY lower(e.nombre_usuario), e.id) FROM elementos e), '[]'::jsonb),
        'total', (SELECT count(*) FROM filtrados),
        'pagina', p_pagina,
        'tamano_pagina', p_tamano,
        'total_paginas', ((SELECT count(*) FROM filtrados) + p_tamano - 1) / p_tamano
    ) INTO v_resultado;
    RETURN v_resultado;
END;
$$;

REVOKE ALL ON FUNCTION public.sarm_listar_usuarios(uuid,text,text,uuid,text,integer,integer)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sarm_listar_usuarios(uuid,text,text,uuid,text,integer,integer)
    TO service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;
