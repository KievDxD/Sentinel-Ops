/**
 * Almacén global de estado con Zustand para la sesión JWT, el Control de Roles (RBAC de 5 niveles)
 * y el Modo Táctico de Campo de Alto Contraste (Sunlight Ready).
 * La sesión se gestiona por pestaña/ventana en sessionStorage para garantizar que al abrir
 * la aplicación siempre solicite autenticación formal si no hay una sesión activa explícita.
 */

import { create } from "zustand";
import type {
  RespuestaTokensAutenticacion,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

const CLAVE_ALMACENAMIENTO_SESION = "sentinel_ops_sesion_jwt_v1";
const CLAVE_MODO_TACTICO = "sentinel_ops_modo_tactico_v2";

interface DatosPersistidosSesion {
  tokenAcceso: string | null;
  tokenRefresco: string | null;
  usuarioActual: UsuarioSistema | null;
}

interface EstadoAutenticacion extends DatosPersistidosSesion {
  modoTacticoAltoContraste: boolean;
  establecerSesion: (respuesta: RespuestaTokensAutenticacion) => void;
  cerrarSesion: () => void;
  alternarModoTactico: () => void;
}

function leerSesionInicial(): DatosPersistidosSesion {
  try {
    // Purgar cualquier residuo en localStorage para evitar que la aplicación arranque con sesión predeterminada
    localStorage.removeItem(CLAVE_ALMACENAMIENTO_SESION);

    const textoGuardado = sessionStorage.getItem(CLAVE_ALMACENAMIENTO_SESION);
    if (!textoGuardado) {
      return { tokenAcceso: null, tokenRefresco: null, usuarioActual: null };
    }
    const datos = JSON.parse(textoGuardado) as DatosPersistidosSesion;
    return {
      tokenAcceso: datos.tokenAcceso ?? null,
      tokenRefresco: datos.tokenRefresco ?? null,
      usuarioActual: datos.usuarioActual ?? null,
    };
  } catch {
    return { tokenAcceso: null, tokenRefresco: null, usuarioActual: null };
  }
}

function leerModoTacticoInicial(): boolean {
  try {
    return localStorage.getItem(CLAVE_MODO_TACTICO) === "true";
  } catch {
    return false;
  }
}

export const usarAlmacenAutenticacion = create<EstadoAutenticacion>(
  (set, get) => ({
    ...leerSesionInicial(),
    modoTacticoAltoContraste: leerModoTacticoInicial(),

    establecerSesion: (respuesta: RespuestaTokensAutenticacion): void => {
      const nuevoEstado: DatosPersistidosSesion = {
        tokenAcceso: respuesta.token_acceso,
        tokenRefresco: respuesta.token_refresco,
        usuarioActual: respuesta.usuario,
      };
      sessionStorage.setItem(
        CLAVE_ALMACENAMIENTO_SESION,
        JSON.stringify(nuevoEstado)
      );
      localStorage.removeItem(CLAVE_ALMACENAMIENTO_SESION);
      set(nuevoEstado);
    },

    cerrarSesion: (): void => {
      sessionStorage.removeItem(CLAVE_ALMACENAMIENTO_SESION);
      localStorage.removeItem(CLAVE_ALMACENAMIENTO_SESION);
      set({
        tokenAcceso: null,
        tokenRefresco: null,
        usuarioActual: null,
      });
    },

    alternarModoTactico: (): void => {
      const siguiente = !get().modoTacticoAltoContraste;
      localStorage.setItem(CLAVE_MODO_TACTICO, String(siguiente));
      set({ modoTacticoAltoContraste: siguiente });
    },
  })
);
