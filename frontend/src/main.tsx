import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { App } from "./App";

const elementoRaiz: HTMLElement | null = document.getElementById("raiz");

if (!elementoRaiz) {
  throw new Error("No se encontró el elemento raíz en el documento HTML.");
}

createRoot(elementoRaiz).render(
  <StrictMode>
    <App />
  </StrictMode>
);

