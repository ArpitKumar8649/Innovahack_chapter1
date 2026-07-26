import { useRef, useEffect } from "react";
import { Link } from "react-router-dom";

/* ------------------------------------------------------------------ */
/*  WebGL shader background — animated concentric rose rings           */
/* ------------------------------------------------------------------ */

const VERT = `attribute vec2 aPosition; void main() { gl_Position = vec4(aPosition, 0.0, 1.0); }`;

const FRAG = `
precision highp float;
uniform float iTime;
uniform vec2 iResolution;
mat2 rotate2d(float a){ float c=cos(a),s=sin(a); return mat2(c,-s,s,c); }
float variation(vec2 v1, vec2 v2, float strength, float speed){
  return sin(dot(normalize(v1),normalize(v2))*strength + iTime*speed)/100.0;
}
vec3 paintCircle(vec2 uv, vec2 center, float rad, float width){
  vec2 diff = center - uv;
  float len = length(diff);
  len += variation(diff, vec2(0.,1.), 5., 2.);
  len -= variation(diff, vec2(1.,0.), 5., 2.);
  float circle = smoothstep(rad-width, rad, len) - smoothstep(rad, rad+width, len);
  return vec3(circle);
}
void main(){
  vec2 uv = gl_FragCoord.xy / iResolution.xy;
  uv.x *= 1.5; uv.x -= 0.25;
  float mask = 0.0;
  float radius = .35;
  vec2 center = vec2(.5);
  mask += paintCircle(uv, center, radius, .035).r;
  mask += paintCircle(uv, center, radius-.018, .01).r;
  mask += paintCircle(uv, center, radius+.018, .005).r;
  vec2 v = rotate2d(iTime) * uv;
  /* rose foreground: warm pinks instead of cyan/blue */
  vec3 foregroundColor = vec3(0.96 + v.x*0.04, 0.28 + v.y*0.15, 0.37 + v.x*0.1);
  vec3 bgColor = vec3(0.078, 0.024, 0.043);
  vec3 color = mix(bgColor, foregroundColor, mask * 0.35);
  color = mix(color, vec3(1.0, 0.75, 0.8), paintCircle(uv, center, radius, .003).r * 0.5);
  gl_FragColor = vec4(color, 1.);
}`;

function ShaderCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl");
    if (!gl) return;

    const compile = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(prog, "aPosition");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    const iTime = gl.getUniformLocation(prog, "iTime");
    const iRes = gl.getUniformLocation(prog, "iResolution");

    let raf: number;
    const render = (t: number) => {
      gl.uniform1f(iTime, t * 0.001);
      gl.uniform2f(iRes, canvas.width, canvas.height);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      raf = requestAnimationFrame(render);
    };
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    resize();
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(render);
    return () => { window.removeEventListener("resize", resize); cancelAnimationFrame(raf); };
  }, []);

  return <canvas ref={canvasRef} className="pricing-shader" />;
}

/* ------------------------------------------------------------------ */
/*  Ripple button                                                      */
/* ------------------------------------------------------------------ */

function RippleButton({ children, className, onClick }: {
  children: React.ReactNode; className?: string; onClick?: () => void;
}) {
  const btnRef = useRef<HTMLButtonElement>(null);
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const btn = btnRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const ripple = document.createElement("span");
    const size = Math.max(rect.width, rect.height) * 2;
    ripple.className = "ripple";
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
    onClick?.();
  };
  return (
    <button ref={btnRef} className={`ripple-btn ${className ?? ""}`} onClick={handleClick}>
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Pricing data — VeritasAI plans                                     */
/* ------------------------------------------------------------------ */

interface Plan {
  name: string;
  description: string;
  price: string;
  features: string[];
  buttonText: string;
  popular?: boolean;
  variant: "primary" | "secondary";
}

const PLANS: Plan[] = [
  {
    name: "Free",
    description: "Personal fact-checking for the curious.",
    price: "0",
    features: [
      "5 investigations / day",
      "3-agent verifier panel",
      "FEC receipts (SHA-256 + Merkle)",
      "Community support",
    ],
    buttonText: "Get Started",
    variant: "secondary",
  },
  {
    name: "Pro",
    description: "For researchers, journalists, and teams.",
    price: "49",
    features: [
      "Unlimited investigations",
      "Full 10-agent court + Judge",
      "Multi-turn debate transcripts",
      "Semantic counter-evidence (Phase 6)",
      "API access (100 calls/day)",
      "Priority support",
    ],
    buttonText: "Choose Pro",
    popular: true,
    variant: "primary",
  },
  {
    name: "Enterprise",
    description: "White-label verification at scale.",
    price: "149",
    features: [
      "Everything in Pro",
      "White-label API + webhooks",
      "Multi-tenant usage metering",
      "Expert Referee portal",
      "Compliance mode (full reasoning)",
      "Dedicated support + SLA",
    ],
    buttonText: "Contact Us",
    variant: "primary",
  },
];

/* ------------------------------------------------------------------ */
/*  Pricing card                                                       */
/* ------------------------------------------------------------------ */

function CheckIcon() {
  return (
    <svg className="pricing-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function PricingCard({ plan }: { plan: Plan }) {
  return (
    <div className={`pricing-card ${plan.popular ? "popular" : ""}`}>
      {plan.popular && <div className="pricing-badge">Most Popular</div>}
      <div className="pricing-card-head">
        <h2 className="pricing-plan-name display">{plan.name}</h2>
        <p className="pricing-desc">{plan.description}</p>
      </div>
      <div className="pricing-price">
        <span className="pricing-amount display">${plan.price}</span>
        <span className="pricing-period">/mo</span>
      </div>
      <div className="pricing-divider" />
      <ul className="pricing-features">
        {plan.features.map((f, i) => (
          <li key={i}><CheckIcon /> {f}</li>
        ))}
      </ul>
      <RippleButton className={plan.variant === "primary" ? "pricing-cta primary" : "pricing-cta secondary"}>
        {plan.buttonText}
      </RippleButton>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export function Pricing() {
  return (
    <div className="pricing-page">
      <ShaderCanvas />
      <main className="pricing-main wrap">
        <div className="pricing-header">
          <h1 className="pricing-title display">
            Find the <span className="pricing-accent">Perfect Plan</span> for Your Research
          </h1>
          <p className="pricing-subtitle">
            Start free, then scale with the court. Every plan includes
            cryptographically anchored receipts.
          </p>
        </div>
        <div className="pricing-grid">
          {PLANS.map((p) => <PricingCard key={p.name} plan={p} />)}
        </div>
        <p className="pricing-note mono">
          All plans include FEC (SHA-256 + Merkle + signed verdicts) · Cancel anytime
        </p>
        <div className="pricing-back">
          <Link to="/" className="btn">← Back to overview</Link>
        </div>
      </main>
    </div>
  );
}
