/** Whether this browser can make a WebGL context; kept apart from the three.js code so a page can ask before loading it. */
export function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch {
    return false;
  }
}
