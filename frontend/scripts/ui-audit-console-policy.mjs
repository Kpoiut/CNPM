const WEBGL_READ_PIXELS_WARNING = /^\[\.WebGL-[^\]]+\]GL Driver Message .*GPU stall due to ReadPixels/


export function shouldIgnoreAuditConsoleMessage({ type, text }) {
  return type === 'warning' && WEBGL_READ_PIXELS_WARNING.test(text || '')
}
