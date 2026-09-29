"use client";

import React, { useRef, useState, useEffect } from "react";
import Link from "next/link";
import {
  motion,
  useScroll,
  useTransform,
  useInView,
  animate,
} from "framer-motion";
import "./landing.css";

/* ═══════════════════════════════════════════════════════
   Animation Presets
   ═══════════════════════════════════════════════════════ */

const ease = [0.22, 1, 0.36, 1] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease } },
};

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.8 } },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

const staggerFast = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const slideLeft = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } },
};

const slideRight = {
  hidden: { opacity: 0, x: 40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.8, ease } },
};

const clipReveal = {
  hidden: { clipPath: "inset(0 100% 0 0)" },
  visible: {
    clipPath: "inset(0 0% 0 0)",
    transition: { duration: 1.2, ease },
  },
};

const barGrow = (width: string) => ({
  hidden: { scaleX: 0 },
  visible: {
    scaleX: 1,
    transition: { duration: 1, ease },
  },
});

/* ═══════════════════════════════════════════════════════
   Helper Components
   ═══════════════════════════════════════════════════════ */

function Reveal({
  children,
  className,
  variants: v,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  variants?: Record<string, any>;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={v || fadeUp}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}

function StaggerWrap({
  children,
  className,
  fast,
}: {
  children: React.ReactNode;
  className?: string;
  fast?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={fast ? staggerFast : stagger}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function Counter({
  target,
  suffix = "",
  prefix = "",
}: {
  target: number;
  suffix?: string;
  prefix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [val, setVal] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const ctrl = animate(0, target, {
      duration: 2,
      ease: "easeOut",
      onUpdate: (v: number) => setVal(Math.round(v)),
    });
    return () => ctrl.stop();
  }, [inView, target]);

  return (
    <span ref={ref}>
      {prefix}
      {val}
      {suffix}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════
   Data
   ═══════════════════════════════════════════════════════ */

const contributions = [
  { name: "Chest Pain Type", value: 0.38, positive: true },
  { name: "Thalassemia", value: 0.31, positive: true },
  { name: "Major Vessels", value: 0.24, positive: true },
  { name: "Max Heart Rate", value: 0.18, positive: false },
  { name: "ST Depression", value: 0.15, positive: true },
  { name: "Exercise Angina", value: 0.12, positive: true },
];

const engineeringStats = [
  {
    value: 13,
    label: "Structured Inputs",
    desc: "Cardiovascular measurements defined by the model\u2019s feature schema",
  },
  {
    value: 126,
    suffix: "+",
    label: "Automated Tests",
    desc: "Backend, API, and frontend test cases verified on every push",
  },
  {
    value: 6,
    label: "Immutable Artifacts",
    desc: "Cryptographically verified production model bundle",
  },
  {
    static: "<1ms",
    label: "Explanation Latency",
    desc: "Zero-dependency mathematical SHAP-equivalent computation",
  },
  {
    value: 4,
    label: "Pipeline Stages",
    desc: "Automated verify, build, deploy, smoke test",
  },
  {
    static: "0",
    label: "External ML Dependencies",
    desc: "Pure mathematical equivalence replaces SHAP library",
  },
];

/* ═══════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════ */

export default function LandingPage() {
  /* ─── Header scroll state ─── */
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* ─── Model section parallax ─── */
  const modelRef = useRef<HTMLElement>(null);
  const { scrollYProgress: modelProgress } = useScroll({
    target: modelRef,
    offset: ["start end", "end start"],
  });
  const modelImgY = useTransform(modelProgress, [0, 1], ["-8%", "8%"]);


  return (
    <>
      {/* ═══════════════════════════════════════════
          01 · HEADER
          ═══════════════════════════════════════════ */}
      <header className={`lp-header ${scrolled ? "lp-header--scrolled" : ""}`}>
        <div className="lp-header-inner">
          <Link href="/">
            <picture>
              <source
                media="(max-width: 600px)"
                srcSet="/brand/cardiovanta-icon-transparent.png"
              />
              <img
                src="/brand/cardiovanta-horizontal-transparent.png"
                alt="CardioVanta"
                className="lp-header-logo"
              />
            </picture>
          </Link>
          <nav className="lp-header-nav">
            <a href="#intro" className="lp-header-link">About</a>
            <a href="#model" className="lp-header-link">Methodology</a>
            <a href="#engineering" className="lp-header-link">Engineering</a>
            <Link href="/assessment" className="lp-header-cta">
              HEART ANALYSIS &rarr;
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* ═══════════════════════════════════════════
            02 · CINEMATIC HERO
            ═══════════════════════════════════════════ */}
        <section className="lp-hero">
          <video
            src="/videos/a.mp4"
            autoPlay
            muted
            loop
            playsInline
            poster="/images/landing/hero-cardiovascular.jpg"
            className="lp-hero-video"
          />
          <div className="lp-hero-overlay" />
          <div className="lp-hero-glow" />

          <div className="lp-hero-content">
            <motion.span
              className="lp-eyebrow"
              initial={{ opacity: 0, letterSpacing: "0.35em" }}
              animate={{ opacity: 1, letterSpacing: "0.22em" }}
              transition={{ duration: 1, delay: 0.3, ease }}
            >
              Cardiovascular Intelligence
            </motion.span>

            <motion.h1
              className="lp-hero-title"
              initial={{ opacity: 0, y: 40, scaleX: 1.12, scaleY: 0.88 }}
              animate={{ opacity: 1, y: 0, scaleX: 1.12, scaleY: 0.88 }}
              style={{ transformOrigin: "left center" }}
              transition={{ duration: 0.9, delay: 0.5, ease }}
            >
              Understand the signals behind cardiovascular risk.
            </motion.h1>

            <motion.p
              className="lp-hero-sub"
              initial={{ opacity: 0, y: 28 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.75, ease }}
            >
              CardioVanta transforms structured cardiovascular measurements into
              a modelled probability estimate and a transparent explanation of
              the signals behind the prediction.
            </motion.p>

            <motion.div
              className="lp-hero-actions"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 1, ease }}
            >
              <Link href="/assessment" className="btn-primary">
                HEART ANALYSIS &rarr;
              </Link>
              <a href="#pipeline" className="btn-hero-sec">
                HOW IT WORKS &rarr;
              </a>
            </motion.div>
          </div>

          <motion.div
            className="lp-hero-scroll"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.8, duration: 1 }}
          >
            <span>Scroll</span>
            <svg
              className="lp-hero-scroll-chevron"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </motion.div>
        </section>

        {/* ═══════════════════════════════════════════
            03 · TRUST STRIP
            ═══════════════════════════════════════════ */}
        <div className="lp-strip">
          <StaggerWrap className="lp-strip-inner" fast>
            {[
              "13 Model Inputs",
              "Calibrated Probability",
              "Explainable Output",
              "Local Inference",
              "Automated CI/CD",
            ].map((label, i) => (
              <React.Fragment key={label}>
                {i > 0 && <span className="lp-strip-dot" />}
                <motion.span className="lp-strip-item" variants={fadeUp}>
                  {label}
                </motion.span>
              </React.Fragment>
            ))}
          </StaggerWrap>
        </div>

        {/* ═══════════════════════════════════════════
            04 · INTRODUCTION
            ═══════════════════════════════════════════ */}
        <section id="intro" className="lp-intro">
          <div className="lp-intro-grid">
            <Reveal variants={slideLeft} className="lp-intro-text">
              <span className="lp-eyebrow lp-eyebrow--light">
                About CardioVanta
              </span>
              <h2>A clearer way to understand the model.</h2>
              <p>
                CardioVanta brings structured cardiovascular measurements,
                calibrated probability, and model-level explanation together in
                one assessment experience.
              </p>
              <p>
                Every prediction is accompanied by a transparent breakdown of
                the feature contributions that shaped the model&apos;s output&mdash;so
                you can see exactly what the model sees.
              </p>
              <Link href="/assessment" className="btn-secondary">
                Discover CardioVanta &rarr;
              </Link>
            </Reveal>

            <Reveal variants={clipReveal}>
              <div className="lp-intro-visual cv-sample-card">
                <div className="cv-sample-card-header">
                  <h3>Sample assessment</h3>
                  <span className="cv-sample-pill">Illustrative data</span>
                </div>
                
                <div className="cv-sample-card-main">
                  <div className="cv-sample-score-wrap">
                    <div className="cv-sample-score">18.4%</div>
                    <div className="cv-sample-score-sub">Calibrated 10-year risk</div>
                  </div>
                  
                  <div className="cv-sample-scale">
                    <div className="cv-sample-scale-bar">
                      <div className="cv-sample-scale-indicator" style={{ left: '18.4%' }}></div>
                    </div>
                    <div className="cv-sample-scale-labels">
                      <span>Low</span>
                      <span>Moderate</span>
                      <span>High</span>
                    </div>
                  </div>
                </div>

                <div className="cv-sample-card-features">
                  <h4>What shaped this result</h4>
                  
                  <div className="cv-sample-feature">
                    <div className="cv-sample-feature-info">
                      <span className="cv-sample-feature-label">Systolic blood pressure</span>
                      <span className="cv-sample-feature-val">148 mmHg</span>
                    </div>
                    <div className="cv-sample-feature-bar cv-sample-bar-red" style={{ width: '90%' }}></div>
                  </div>
                  
                  <div className="cv-sample-feature">
                    <div className="cv-sample-feature-info">
                      <span className="cv-sample-feature-label">Age</span>
                      <span className="cv-sample-feature-val">61 years</span>
                    </div>
                    <div className="cv-sample-feature-bar cv-sample-bar-red" style={{ width: '45%' }}></div>
                  </div>
                  
                  <div className="cv-sample-feature">
                    <div className="cv-sample-feature-info">
                      <span className="cv-sample-feature-label">LDL cholesterol</span>
                      <span className="cv-sample-feature-val">162 mg/dL</span>
                    </div>
                    <div className="cv-sample-feature-bar cv-sample-bar-red" style={{ width: '35%' }}></div>
                  </div>
                  
                  <div className="cv-sample-feature">
                    <div className="cv-sample-feature-info">
                      <span className="cv-sample-feature-label">Resting heart rate</span>
                      <span className="cv-sample-feature-val">64 bpm</span>
                    </div>
                    <div className="cv-sample-feature-bar cv-sample-bar-green" style={{ width: '25%' }}></div>
                  </div>
                  
                  <div className="cv-sample-feature">
                    <div className="cv-sample-feature-info">
                      <span className="cv-sample-feature-label">Physical activity</span>
                      <span className="cv-sample-feature-val">4 days / week</span>
                    </div>
                    <div className="cv-sample-feature-bar cv-sample-bar-green" style={{ width: '35%' }}></div>
                  </div>
                </div>

                <div className="cv-sample-card-legend">
                  <span className="cv-sample-legend-item cv-sample-legend-red">Raises risk</span>
                  <span className="cv-sample-legend-item cv-sample-legend-green">Lowers risk</span>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            05 · PIPELINE — HOW IT WORKS
            ═══════════════════════════════════════════ */}
        <section id="pipeline" className="lp-pipeline">
          <div className="lp-pipeline-inner">
            <Reveal className="lp-pipeline-header">
              <span className="lp-eyebrow lp-eyebrow--light">
                How It Works
              </span>
              <h2>Built around clarity.</h2>
              <p>
                CardioVanta is designed to make the journey from structured
                cardiovascular input to model output easier to understand.
              </p>
            </Reveal>

            <StaggerWrap className="lp-pipeline-grid">
              <motion.div className="lp-pipeline-step" variants={fadeUp}>
                <div className="lp-step-num">01</div>
                <div className="lp-step-title">Structured Inputs</div>
                <div className="lp-step-desc">
                  13 cardiovascular measurements are collected using the
                  model&apos;s defined feature schema. Each input is validated
                  against development-data guardrails before inference.
                </div>
                <Link href="/assessment" className="lp-step-link">
                  Explore assessment &rarr;
                </Link>
              </motion.div>

              <motion.div className="lp-pipeline-step" variants={fadeUp}>
                <div className="lp-step-num">02</div>
                <div className="lp-step-title">Calibrated Probability</div>
                <div className="lp-step-desc">
                  The production model returns a Platt-scaled calibrated
                  probability estimate, designed to be interpretable as a
                  meaningful probability rather than a raw score.
                </div>
                <Link href="/assessment" className="lp-step-link">
                  See the result &rarr;
                </Link>
              </motion.div>

              <motion.div className="lp-pipeline-step" variants={fadeUp}>
                <div className="lp-step-num">03</div>
                <div className="lp-step-title">Transparent Explanation</div>
                <div className="lp-step-desc">
                  A dedicated explanation model exposes the SHAP-equivalent
                  feature contributions behind the underlying model
                  output&mdash;with zero external dependencies.
                </div>
                <Link href="/assessment" className="lp-step-link">
                  Understand the explanation &rarr;
                </Link>
              </motion.div>
            </StaggerWrap>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            06 · MODEL INTELLIGENCE (PARALLAX)
            ═══════════════════════════════════════════ */}
        <section id="model" className="lp-model" ref={modelRef}>
          <div className="lp-model-img-wrap">
            <motion.img
              src="/images/landing/bg-model-hq.png"
              alt="ML pipeline visualization"
              style={{ y: modelImgY }}
            />
          </div>
          <div className="lp-model-overlay" />
          <div className="lp-model-glow" />

          <div className="lp-model-content">
            <Reveal>
              <span className="lp-eyebrow">Model Methodology</span>
            </Reveal>
            <Reveal>
              <h2>From measurements to modelled probability.</h2>
            </Reveal>
            <Reveal>
              <p>
                Thirteen structured measurements move through the CardioVanta
                production inference pipeline, generating a calibrated
                probability with full feature-level attribution.
              </p>
            </Reveal>

            <StaggerWrap className="lp-model-details">
              <motion.div className="lp-model-detail" variants={fadeUp}>
                <h4>Logistic Regression</h4>
                <p>
                  Linear model with interpretable coefficients. No opaque
                  neural architectures.
                </p>
              </motion.div>
              <motion.div className="lp-model-detail" variants={fadeUp}>
                <h4>Platt Scaling</h4>
                <p>
                  Sigmoid calibration transforms raw scores into meaningful
                  probability estimates.
                </p>
              </motion.div>
              <motion.div className="lp-model-detail" variants={fadeUp}>
                <h4>SHAP-Equivalent</h4>
                <p>
                  Mathematical equivalence to SHAP, computed in under 1ms with
                  zero library overhead.
                </p>
              </motion.div>
              <motion.div className="lp-model-detail" variants={fadeUp}>
                <h4>Strict Isolation</h4>
                <p>
                  Locked development/test split. The test set was never used
                  for training, tuning, or calibration.
                </p>
              </motion.div>
            </StaggerWrap>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            07 · EXPLAINABILITY SHOWCASE
            ═══════════════════════════════════════════ */}
        <section className="lp-explain">
          <div className="lp-explain-grid">
            <Reveal variants={slideLeft} className="lp-explain-text">
              <span className="lp-eyebrow lp-eyebrow--light">
                Explainability
              </span>
              <h2>Every prediction, explained.</h2>
              <p>
                CardioVanta doesn&apos;t just produce a number. Every
                prediction includes a breakdown of the individual feature
                contributions that shaped the model&apos;s output, using
                SHAP-equivalent linear attribution relative to the frozen
                development background.
              </p>
            </Reveal>

            <Reveal variants={slideRight}>
              <div className="lp-explain-panel">
                <div className="lp-explain-panel-header">
                  <span className="lp-explain-panel-title">
                    Feature Contributions
                  </span>
                  <span className="lp-explain-panel-tag">Illustrative</span>
                </div>

                <StaggerWrap fast>
                  {contributions.map((f) => (
                    <motion.div
                      key={f.name}
                      className="lp-explain-feature"
                      variants={fadeUp}
                    >
                      <span className="lp-explain-label">{f.name}</span>
                      <div className="lp-explain-bar-track">
                        <Reveal
                          variants={barGrow(`${f.value * 100}%`)}
                          style={{
                            width: `${f.value * 100}%`,
                            transformOrigin: "left center",
                          }}
                        >
                          <div
                            className={`lp-explain-bar-fill ${
                              f.positive
                                ? "lp-explain-bar-fill--pos"
                                : "lp-explain-bar-fill--neg"
                            }`}
                            style={{ width: "100%", height: "28px" }}
                          />
                        </Reveal>
                      </div>
                      <span className="lp-explain-val">
                        {f.positive ? "+" : "\u2212"}
                        {f.value.toFixed(2)}
                      </span>
                    </motion.div>
                  ))}
                </StaggerWrap>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            08 · IMAGE SHOWCASE
            ═══════════════════════════════════════════ */}
        <div className="lp-showcase">
          <Reveal variants={fadeIn}>
            <img
              src="/images/landing/assessment-transition.jpg"
              alt="Cardiovascular research"
              className="lp-showcase-img"
            />
          </Reveal>
          <div className="lp-showcase-overlay" />
        </div>

        {/* ═══════════════════════════════════════════
            09 · ENGINEERING STATS
            ═══════════════════════════════════════════ */}
        <section id="engineering" className="lp-eng">
          <div className="lp-eng-inner">
            <Reveal className="lp-eng-header">
              <span className="lp-eyebrow lp-eyebrow--light">
                Engineering
              </span>
              <h2>Rigorous by design.</h2>
              <p>
                Every component of CardioVanta&mdash;from feature validation
                to production deployment&mdash;is built for reproducibility,
                testability, and artifact integrity.
              </p>
            </Reveal>

            <StaggerWrap className="lp-eng-grid">
              {engineeringStats.map((stat) => (
                <motion.div
                  key={stat.label}
                  className="lp-eng-card"
                  variants={fadeUp}
                >
                  <div className="lp-eng-num">
                    {stat.value !== undefined ? (
                      <Counter
                        target={stat.value}
                        suffix={stat.suffix || ""}
                      />
                    ) : (
                      stat.static
                    )}
                  </div>
                  <div className="lp-eng-label">{stat.label}</div>
                  <div className="lp-eng-desc">{stat.desc}</div>
                </motion.div>
              ))}
            </StaggerWrap>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            10 · MONITORING & RELIABILITY
            ═══════════════════════════════════════════ */}
        <section className="lp-monitor">
          <div className="lp-monitor-grid">
            <Reveal variants={slideLeft} className="lp-monitor-text">
              <span className="lp-eyebrow">Production</span>
              <h2>Monitored and verified.</h2>
              <p>
                CardioVanta runs a fully automated CI/CD pipeline that
                verifies backend integrity, frontend builds, and production
                deployments on every push to main.
              </p>
              <p>
                Drift detection uses two-sample KS statistics with Monte Carlo
                permutation testing and support-boundary checks to identify
                distributional shifts in incoming data.
              </p>

              <div className="lp-monitor-indicators">
                <div className="lp-monitor-indicator">
                  <span className="lp-monitor-dot" />
                  Backend verification passing
                </div>
                <div className="lp-monitor-indicator">
                  <span className="lp-monitor-dot" />
                  Frontend verification passing
                </div>
                <div className="lp-monitor-indicator">
                  <span className="lp-monitor-dot" />
                  Production deployment verified
                </div>
                <div className="lp-monitor-indicator">
                  <span className="lp-monitor-dot" />
                  Post-deploy smoke tests passing
                </div>
              </div>
            </Reveal>

          </div>
        </section>

        {/* ═══════════════════════════════════════════
            11 · RESPONSIBLE USE
            ═══════════════════════════════════════════ */}
        <section className="lp-responsible">
          <div className="lp-responsible-inner">
            <Reveal className="lp-responsible-header">
              <span className="lp-eyebrow lp-eyebrow--light">
                Responsible Use
              </span>
              <h2>Built with clear boundaries.</h2>
              <p>
                CardioVanta is transparent about what it is and what it is not.
              </p>
            </Reveal>

            <StaggerWrap className="lp-responsible-grid">
              <motion.div className="lp-responsible-card" variants={fadeUp}>
                <svg className="lp-responsible-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <h4>Not Clinically Validated</h4>
                <p>
                  CardioVanta is an ML-based cardiovascular risk assessment
                  application intended for engineering and research use. It is
                  not a medical device and is not intended for clinical
                  diagnosis, treatment, or medical advice.
                </p>
              </motion.div>

              <motion.div className="lp-responsible-card" variants={fadeUp}>
                <svg className="lp-responsible-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
                <h4>Educational Purpose</h4>
                <p>
                  This platform is a demonstration of machine learning
                  techniques&mdash;including calibrated probability estimation,
                  SHAP-equivalent explainability, and serverless
                  deployment&mdash;for educational and evaluation purposes.
                </p>
              </motion.div>

              <motion.div className="lp-responsible-card" variants={fadeUp}>
                <svg className="lp-responsible-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <h4>Privacy by Design</h4>
                <p>
                  Raw clinical feature inputs are excluded from telemetry.
                  Sensitive prediction-output telemetry remains subject to
                  retention and access controls. No personally identifiable
                  information is collected or stored.
                </p>
              </motion.div>

              <motion.div className="lp-responsible-card" variants={fadeUp}>
                <svg className="lp-responsible-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <h4>Acknowledged Limitations</h4>
                <p>
                  Trained on a small dataset (UCI Heart Disease). No
                  post-prediction clinical outcomes are collected. The model
                  reflects observed associations in the development sample and
                  does not imply clinical causality.
                </p>
              </motion.div>
            </StaggerWrap>
          </div>
        </section>

        {/* ═══════════════════════════════════════════
            12 · FINAL CTA
            ═══════════════════════════════════════════ */}
        <section className="lp-cta">
          <div className="lp-cta-glow" />
          <div className="lp-cta-content">
            <Reveal>
              <span className="lp-eyebrow">Ready to Begin?</span>
            </Reveal>
            <Reveal>
              <h2>A clearer read starts here.</h2>
            </Reveal>
            <Reveal>
              <p>
                Explore the CardioVanta assessment and see how structured
                cardiovascular measurements become an interpretable model
                output with a transparent view of the signals behind it.
              </p>
            </Reveal>
            <Reveal>
              <div className="lp-cta-actions">
                <Link href="/assessment" className="btn-primary">
                  HEART ANALYSIS &rarr;
                </Link>
                <a href="#pipeline" className="btn-hero-sec">
                  HOW IT WORKS &rarr;
                </a>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      {/* ═══════════════════════════════════════════
          13 · FOOTER
          ═══════════════════════════════════════════ */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <div className="lp-footer-top">
            <div>
              <img
                src="/brand/cardiovanta-horizontal-transparent.png"
                alt="CardioVanta"
                className="lp-footer-brand-logo"
              />
              <div className="lp-footer-tagline">
                Intelligent cardiovascular insight.
              </div>
            </div>

            <div>
              <div className="lp-footer-col-title">Navigation</div>
              <nav className="lp-footer-links">
                <Link href="/assessment">Assessment</Link>
                <a href="#intro">About</a>
                <a href="#pipeline">How It Works</a>
              </nav>
            </div>

            <div>
              <div className="lp-footer-col-title">Methodology</div>
              <nav className="lp-footer-links">
                <a href="#model">Model</a>
                <a href="#engineering">Engineering</a>
              </nav>
            </div>

            <div>
              <div className="lp-footer-col-title">Project</div>
              <nav className="lp-footer-links">
                <a
                  href="https://github.com/septilex/CardioVanta"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </nav>
            </div>
          </div>

          <hr className="lp-footer-divider" />

          <div className="lp-footer-disclaimer">
            CardioVanta is a demonstration of machine learning techniques for
            educational and evaluation purposes. It is not a medical device and
            is not intended for clinical diagnosis, treatment, or medical
            advice.
          </div>
          <div className="lp-footer-copyright">
            &copy; 2026 CardioVanta
          </div>
        </div>
      </footer>
    </>
  );
}
