/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Full INTLLM backend base URL, e.g. http://127.0.0.1:8000 */
  readonly VITE_INTLLM_BASE_URL?: string;
  /** INTLLM backend host used when VITE_INTLLM_BASE_URL is not set. */
  readonly VITE_INTLLM_HOST?: string;
  /** INTLLM backend port used when VITE_INTLLM_BASE_URL is not set. */
  readonly VITE_INTLLM_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module '*.png' {
  const value: string;
  export default value;
}

declare module '*.ico' {
  const value: string;
  export default value;
}

declare module '*.svg' {
  const value: string;
  export default value;
}
