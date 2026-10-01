import { DEPTH } from "@/components/landing/hero-scene";

/**
 * The hero's depth renderer: one full-screen triangle strip and a fragment
 * shader that re-projects the scale-model render through its depth map.
 *
 * Two effects, both cheap enough for a phone GPU:
 * - parallax: each pixel is sampled from where its depth says it came from,
 *   so near walls and far walls slide past each other as the offset changes;
 * - the survey scan: a vertical plane sweeps the model and lights the line
 *   where it meets a surface, climbing walls and machines as it crosses them.
 *
 * Loaded with a dynamic import after the hero image has painted; the image
 * underneath stays the content (and the fallback) throughout. Nothing here
 * runs a loop of its own: the caller renders a frame when something changed.
 */

const VERTEX = `
attribute vec2 aPos;
varying vec2 vUv;
void main() {
  vUv = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5);
  gl_Position = vec4(aPos, 0.0, 1.0);
}`;

const fragment = (derivatives: boolean) => `${derivatives ? "#extension GL_OES_standard_derivatives : enable\n#define HAS_DERIVATIVES 1" : ""}
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform sampler2D uColor;
uniform sampler2D uDepth;
uniform vec2 uOffset;
uniform float uFocus;
uniform vec3 uAxis;
uniform vec2 uRange;
uniform vec4 uGround;
uniform float uGround0;
uniform float uScan;
uniform float uScanAmount;
varying vec2 vUv;

void main() {
  // Backward warp: find the source point that the offset carries onto this
  // pixel. Six fixed-point steps converge for offsets this small.
  vec2 uv = vUv;
  for (int i = 0; i < 6; i++) {
    uv = vUv - (texture2D(uDepth, uv).r - uFocus) * uOffset;
  }
  vec3 color = texture2D(uColor, uv).rgb;

  if (uScanAmount > 0.001) {
    float depth = texture2D(uDepth, uv).r;
    float ground = dot(uGround, vec4(uv.x, uv.y, uv.x * uv.y, uv.y * uv.y)) + uGround0;
    float onModel = smoothstep(0.02, 0.06, depth - ground);
    // A blurred depth (mip bias) for the scan coordinate: the contour of a
    // smooth field is a clean sweep, of a noisy one a jagged line.
    float smoothDepth = texture2D(uDepth, uv, 4.2).r;
    float s = (dot(uAxis, vec3(uv, smoothDepth)) - uRange.x) / (uRange.y - uRange.x);
    float k = s - uScan;
#ifdef HAS_DERIVATIVES
    float px = length(vec2(dFdx(s), dFdy(s))) + 1e-5;
#else
    float px = 0.0012;
#endif
    // A soft sheet of light rather than a crisp line: a sharp edge over the
    // model's steps read as a crackle, which is the wrong note here.
    float line = exp(-(k * k) / (2.0 * (1.4 * px) * (1.4 * px)));
    float glow = exp(-(k * k) / (2.0 * (18.0 * px) * (18.0 * px)));
    float trail = (1.0 - smoothstep(-0.0005, 0.0005, k)) * exp(k * 9.0);
    vec3 ice = vec3(0.647, 0.784, 1.0);
    float amount = uScanAmount * onModel;
    color = mix(color, color * 0.86 + ice * 0.16, trail * 0.55 * amount);
    color += ice * (line * 0.55 + glow * 0.26) * amount;
  }
  gl_FragColor = vec4(color, 1.0);
}`;

export type DepthFrame = {
  /** Parallax, in UV per unit of depth away from the focus. Keep |x|,|y| ≲ 0.02. */
  offsetX: number;
  offsetY: number;
  /** Scan front, 0..1 along the sweep (see hero-scene.ts). */
  scan: number;
  /** 0 hides the scan entirely. */
  scanAmount: number;
};

export type DepthRenderer = {
  /** (Re)uploads the colour image at the canvas's device-pixel size. */
  setImage(image: HTMLImageElement): void;
  /** Matches the drawing buffer to the canvas's CSS box. Returns true if it changed. */
  resize(): boolean;
  render(frame: DepthFrame): void;
  dispose(): void;
};

type Options = {
  /** Called once if the GPU drops the context; the caller should fall back. */
  onLost: () => void;
  /** Accept a software rasteriser (headless test browsers only). */
  allowSoftware?: boolean;
};

const MAX_DPR = 2;

export function createDepthRenderer(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  depth: HTMLImageElement,
  { onLost, allowSoftware = false }: Options,
): DepthRenderer | null {
  const gl = canvas.getContext("webgl", {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    premultipliedAlpha: false,
    preserveDrawingBuffer: false,
    powerPreference: "low-power",
    // A software rasteriser would run the scan on the CPU: not worth it.
    failIfMajorPerformanceCaveat: !allowSoftware,
  });
  if (!gl) return null;

  const derivatives = gl.getExtension("OES_standard_derivatives") !== null;
  const program = link(gl, VERTEX, fragment(derivatives));
  if (!program) return null;
  gl.useProgram(program);

  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(program, "aPos");
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const colorTexture = gl.createTexture();
  const depthTexture = gl.createTexture();
  if (!colorTexture || !depthTexture) return null;

  // Depth is data, not a picture: no colour management, and mipmaps (the map
  // is 1024×512 on purpose) for the blurred lookup the scan uses.
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, depthTexture);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, depth);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  clampToEdge(gl);

  const uniform = (name: string) => gl.getUniformLocation(program, name);
  gl.uniform1i(uniform("uColor"), 0);
  gl.uniform1i(uniform("uDepth"), 1);
  gl.uniform1f(uniform("uFocus"), DEPTH.focus);
  gl.uniform3f(uniform("uAxis"), ...DEPTH.scanAxis);
  gl.uniform2f(uniform("uRange"), ...DEPTH.scanRange);
  gl.uniform4f(uniform("uGround"), DEPTH.ground[0], DEPTH.ground[1], DEPTH.ground[2], DEPTH.ground[3]);
  gl.uniform1f(uniform("uGround0"), DEPTH.ground[4]);
  const uOffset = uniform("uOffset");
  const uScan = uniform("uScan");
  const uScanAmount = uniform("uScanAmount");

  // The colour texture is the hero <img> redrawn at the canvas's own pixel
  // size by the browser's high-quality scaler. Sampling a 1800px source into
  // a 700px canvas without mipmaps would shimmer as soon as it moves.
  const scratch = document.createElement("canvas");
  const scratch2d = scratch.getContext("2d");

  let lost = false;
  let uploadedFor = "";
  const handleLost = (event: Event) => {
    event.preventDefault();
    if (lost) return;
    lost = true;
    onLost();
  };
  canvas.addEventListener("webglcontextlost", handleLost);

  const renderer: DepthRenderer = {
    resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
      const width = Math.max(1, Math.round(canvas.clientWidth * dpr));
      const height = Math.max(1, Math.round(canvas.clientHeight * dpr));
      if (canvas.width === width && canvas.height === height) return false;
      canvas.width = width;
      canvas.height = height;
      return true;
    },

    setImage(source) {
      if (lost || !scratch2d || !source.naturalWidth) return;
      const key = `${source.currentSrc}|${canvas.width}x${canvas.height}`;
      if (key === uploadedFor) return;
      uploadedFor = key;
      scratch.width = canvas.width;
      scratch.height = canvas.height;
      scratch2d.imageSmoothingEnabled = true;
      scratch2d.imageSmoothingQuality = "high";
      scratch2d.drawImage(source, 0, 0, scratch.width, scratch.height);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, colorTexture);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.BROWSER_DEFAULT_WEBGL);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, scratch);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      clampToEdge(gl);
      // The GPU has its copy; don't keep a second full-size bitmap around.
      scratch.width = 1;
      scratch.height = 1;
    },

    render({ offsetX, offsetY, scan, scanAmount }) {
      if (lost) return;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(uOffset, offsetX, offsetY);
      gl.uniform1f(uScan, scan);
      gl.uniform1f(uScanAmount, scanAmount);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    },

    dispose() {
      canvas.removeEventListener("webglcontextlost", handleLost);
      if (lost) return;
      gl.deleteTexture(colorTexture);
      gl.deleteTexture(depthTexture);
      gl.deleteBuffer(quad);
      gl.deleteProgram(program);
      // Hand the context back now rather than at garbage collection: browsers
      // cap live contexts, and a client-side navigation away and back would
      // otherwise hold two.
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    },
  };

  renderer.resize();
  renderer.setImage(image);
  return renderer;
}

function clampToEdge(gl: WebGLRenderingContext) {
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
}

function link(gl: WebGLRenderingContext, vertexSource: string, fragmentSource: string) {
  const vertex = compile(gl, gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  if (!vertex || !fragmentShader || !program) return null;
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragmentShader);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    return null;
  }
  return program;
}

function compile(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}
