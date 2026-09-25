import React from "react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <>
      {/* 01 — INSTITUTIONAL HEADER */}
      <header className="landing-header">
        <div className="container">
          <div className="logo-wrapper">
            <Link href="/">
              <picture>
                <source media="(max-width: 600px)" srcSet="/brand/cardiovanta-icon-transparent.png" />
                <img src="/brand/cardiovanta-horizontal-transparent.png" alt="CardioVanta" className="brand-logo" />
              </picture>
            </Link>
          </div>
          <nav className="landing-nav">
            <a href="#intro" className="nav-link">About</a>
            <a href="#how" className="nav-link">How It Works</a>
            <a href="#model" className="nav-link">Model</a>
            <Link href="/assessment" className="btn-primary" style={{ padding: '12px 24px', fontSize: '14px' }}>
              HEART ANALYSIS &rarr;
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* 02 — FULL-WIDTH HERO */}
        <section className="landing-hero" style={{ position: 'relative', padding: '160px 0 80px 0', overflow: 'hidden' }}>
          <video 
            src="/videos/a.mp4" 
            autoPlay 
            muted 
            loop 
            playsInline 
            poster="/images/landing/hero-cardiovascular.jpg"
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 0 }}
          />
          <div className="hero-bg" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'linear-gradient(to right, rgba(18, 16, 15, 0.95) 0%, rgba(18, 16, 15, 0.7) 35%, rgba(18, 16, 15, 0.2) 100%)', zIndex: 1 }}></div>
          <div style={{ position: 'relative', zIndex: 2, paddingLeft: '12%', paddingRight: '10%', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '40px' }}>
            <div style={{ maxWidth: '800px' }}>
              <span className="hero-eyebrow">Cardiovascular Intelligence</span>
              <h1 className="hero-h1">Understand the signals behind cardiovascular risk.</h1>
              <p className="hero-sub" style={{ color: '#EFE9E0', marginBottom: 0 }}>
                CardioVanta transforms structured cardiovascular measurements into a modelled probability estimate and a transparent explanation of the signals behind the prediction.
              </p>
            </div>
            <div className="hero-actions" style={{ marginTop: 0, flexShrink: 0, paddingBottom: '8px' }}>
              <Link href="/assessment" className="btn-primary">
                HEART ANALYSIS &rarr;
              </Link>
              <a href="#how" className="btn-hero-sec">
                HOW IT WORKS &rarr;
              </a>
            </div>
          </div>
        </section>

        {/* 03 — CAPABILITY / TRUST STRIP */}
        <div className="landing-strip">
          <div className="container strip-items">
            <span>13 MODEL INPUTS</span>
            <span className="strip-dot">&bull;</span>
            <span>CALIBRATED PROBABILITY</span>
            <span className="strip-dot">&bull;</span>
            <span>EXPLAINABLE OUTPUT</span>
            <span className="strip-dot">&bull;</span>
            <span>LOCAL INFERENCE</span>
          </div>
        </div>

        {/* 04 — CARDIOVANTA INTRODUCTION */}
        <section id="intro" className="editorial-section" style={{ paddingTop: '80px', paddingBottom: '80px' }}>
          <div className="container ed-grid" style={{ gridTemplateColumns: '45% 55%', gap: '80px' }}>
            <div className="ed-text">
              <h2>A clearer way to understand the model.</h2>
              <p>
                CardioVanta brings structured cardiovascular measurements, calibrated probability, and model-level explanation together in one assessment experience.
              </p>
              <Link href="/assessment" className="btn-secondary">
                Discover CardioVanta &rarr;
              </Link>
            </div>
            <div className="ed-visual" style={{ padding: 0, overflow: 'hidden', border: 'none', backgroundColor: 'transparent', height: '550px' }}>
              <img src="/images/landing/clinical-care.jpg" alt="Clinical Care" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '4px' }} />
            </div>
          </div>
        </section>

        {/* 05 — INTELLIGENCE / MODEL SECTION */}
        <section id="model" className="editorial-section" style={{ backgroundColor: 'var(--cv-white)', paddingTop: '80px', paddingBottom: '80px' }}>
          <div className="container ed-grid" style={{ gridTemplateColumns: '55% 45%', gap: '80px' }}>
            <div className="ed-visual" style={{ padding: 0, overflow: 'hidden', border: 'none', backgroundColor: 'transparent', height: '500px' }}>
              <img src="/images/landing/media_1790144552348.png" alt="Model Intelligence" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '4px' }} />
            </div>
            <div className="ed-text">
              <h2>From measurements to modelled probability.</h2>
              <p>
                Thirteen structured measurements move through the CardioVanta production inference pipeline to generate a modelled probability estimate.
              </p>
              <a href="#how" className="btn-secondary">
                How the assessment works &rarr;
              </a>
            </div>
          </div>
        </section>

        {/* 06 — THREE CAPABILITY BLOCKS */}
        <section id="how" className="how-section">
          <div className="container">
            <div className="how-header">
              <h2>Built around clarity.</h2>
              <p>
                CardioVanta is designed to make the journey from structured cardiovascular input to model output easier to understand.
              </p>
            </div>
            <div className="how-grid">
              <div className="how-card">
                <div className="how-num">01</div>
                <div className="how-title">STRUCTURED INPUTS</div>
                <div className="how-desc">13 cardiovascular measurements are collected using the model's defined feature schema.</div>
                <Link href="/assessment" style={{ color: 'var(--cv-red)', fontWeight: 600, display: 'inline-block', marginTop: '24px' }}>Explore assessment &rarr;</Link>
              </div>
              <div className="how-card">
                <div className="how-num">02</div>
                <div className="how-title">CALIBRATED PROBABILITY</div>
                <div className="how-desc">The production model returns a calibrated probability estimate.</div>
                <Link href="/assessment" style={{ color: 'var(--cv-red)', fontWeight: 600, display: 'inline-block', marginTop: '24px' }}>See the result &rarr;</Link>
              </div>
              <div className="how-card">
                <div className="how-num">03</div>
                <div className="how-title">TRANSPARENT EXPLANATION</div>
                <div className="how-desc">A dedicated explanation model exposes the feature contributions behind the underlying model output.</div>
                <Link href="/assessment" style={{ color: 'var(--cv-red)', fontWeight: 600, display: 'inline-block', marginTop: '24px' }}>Understand the explanation &rarr;</Link>
              </div>
            </div>
          </div>
        </section>

        {/* 07 — HEART ANALYSIS ENTRY SECTION */}
        <section className="entry-section" style={{ padding: 0, position: 'relative' }}>
          <div style={{ backgroundImage: 'url(/images/landing/assessment-transition.jpg)', backgroundSize: 'cover', backgroundPosition: 'center', height: '450px', width: '100%' }}></div>
          <div style={{ padding: '100px 0', backgroundColor: 'var(--cv-warm-white)', textAlign: 'center' }}>
            <div className="container">
              <span className="entry-eyebrow">READY TO BEGIN?</span>
              <h2 className="entry-heading">Explore your cardiovascular profile.</h2>
              <p className="entry-sub">
                Enter the available cardiovascular measurements and let CardioVanta generate a modelled probability estimate with a transparent view of the model signals behind it.
              </p>
              <Link href="/assessment" className="btn-primary" style={{ padding: '20px 48px', fontSize: '18px' }}>
                HEART ANALYSIS &rarr;
              </Link>
            </div>
          </div>
        </section>

        {/* 08 — FINAL CTA */}
        <section className="final-cta">
          <div className="container">
            <h2 style={{ fontSize: '48px', marginBottom: '24px' }}>A clearer read starts here.</h2>
            <p style={{ fontSize: '20px', color: 'var(--cv-text-muted)', maxWidth: '700px', margin: '0 auto 48px' }}>
              Explore the CardioVanta assessment and see how structured cardiovascular measurements become an interpretable model output.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '24px' }}>
              <Link href="/assessment" className="btn-primary">
                HEART ANALYSIS &rarr;
              </Link>
              <a href="#how" className="btn-secondary">
                HOW IT WORKS &rarr;
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* 09 — FOOTER */}
      <footer className="landing-footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <img src="/brand/cardiovanta-horizontal-transparent.png" alt="CardioVanta" className="footer-logo-img" style={{ filter: 'brightness(0) invert(1)' }} />
              <div className="footer-tagline">Intelligent cardiovascular insight.</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', letterSpacing: '0.15em', textTransform: 'uppercase', color: '#8C8279', marginBottom: '24px', fontWeight: 600 }}>Navigation</div>
              <nav className="footer-nav">
                <Link href="/assessment">Assessment</Link>
                <a href="#how">How It Works</a>
                <a href="#intro">About</a>
                <a href="#model">Model</a>
              </nav>
            </div>
          </div>
          <div className="footer-disclaimer">
            CardioVanta is a demonstration of machine learning techniques for educational and evaluation purposes. It is not a medical device and is not intended for clinical diagnosis, treatment, or medical advice.
          </div>
          <div className="footer-copyright">
            &copy; 2026 CardioVanta
          </div>
        </div>
      </footer>
    </>
  );
}
