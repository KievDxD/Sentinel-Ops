/**
 * Almacén global de estado con Zustand para la sesión JWT, el Control de Roles (RBAC de 5 niveles)
 * y el Modo Táctico de Campo de Alto Contraste (Sunlight Ready) persistido en localStorage.
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
    const textoGuardado = localStorage.getItem(CLAVE_ALMACENAMIENTO_SESION);
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
      localStorage.setItem(
        CLAVE_ALMACENAMIENTO_SESION,
        JSON.stringify(nuevoEstado)
      );
      set(nuevoEstado);
    },

    cerrarSesion: (): void => {
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
