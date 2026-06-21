import { type Lang, LANGS, LANG_LABEL } from "./i18n";

type T = (k: string) => string;

/* ---- simple, captioned SVG mockups of each real screen (sound-optional) ---- */
function PasteSVG() {
  return (
    <svg viewBox="0 0 120 80" className="stepart" aria-hidden="true">
      <rect x="8" y="26" width="104" height="22" rx="6" className="s-box" />
      <text x="18" y="41" className="s-link">https://…/video</text>
      <g className="s-accent">
        <rect x="86" y="14" width="20" height="26" rx="3" />
        <rect x="90" y="11" width="12" height="6" rx="2" />
      </g>
    </svg>
  );
}
function FormatSVG() {
  return (
    <svg viewBox="0 0 120 80" className="stepart" aria-hidden="true">
      <rect x="10" y="30" width="48" height="22" rx="11" className="s-pill on" />
      <text x="22" y="45" className="s-pilltxt">▶</text>
      <rect x="62" y="30" width="48" height="22" rx="11" className="s-pill" />
      <text x="80" y="45" className="s-pilltxt dim">♪</text>
    </svg>
  );
}
function DownloadSVG() {
  return (
    <svg viewBox="0 0 120 80" className="stepart" aria-hidden="true">
      <rect x="12" y="34" width="96" height="12" rx="6" className="s-track" />
      <rect x="12" y="34" width="66" height="12" rx="6" className="s-fill" />
      <g className="s-accent">
        <line x1="60" y1="14" x2="60" y2="28" />
        <polyline points="54,23 60,29 66,23" />
      </g>
    </svg>
  );
}
function OfflineSVG() {
  return (
    <svg viewBox="0 0 120 80" className="stepart" aria-hidden="true">
      <rect x="44" y="12" width="32" height="56" rx="6" className="s-box" />
      <polygon points="55,32 55,48 69,40" className="s-fill" />
      <g className="s-accent">
        <path d="M30 20 q10 -10 20 0" />
        <line x1="26" y1="16" x2="54" y2="44" className="s-slash" />
      </g>
    </svg>
  );
}

function Step({ n, icon, title, desc }: { n: number; icon: JSX.Element; title: string; desc: string }) {
  return (
    <div className="lstep reveal">
      <div className="lstep-num">{n}</div>
      <div className="lstep-art">{icon}</div>
      <h3>{title}</h3>
      <p>{desc}</p>
    </div>
  );
}

function Use({ emoji, label }: { emoji: string; label: string }) {
  return (
    <div className="usecard">
      <span className="useemoji" aria-hidden="true">{emoji}</span>
      <span className="uselabel">{label}</span>
    </div>
  );
}

export default function Landing({
  t, lang, setLang, onStart,
}: { t: T; lang: Lang; setLang: (l: Lang) => void; onStart: () => void }) {
  return (
    <div className="landing">
      <div className="langbar">
        {LANGS.map((l) => (
          <button key={l} className={"langbtn" + (l === lang ? " on" : "")}
            onClick={() => setLang(l)} aria-pressed={l === lang}>
            {LANG_LABEL[l]}
          </button>
        ))}
      </div>

      {/* hero */}
      <section className="lhero reveal">
        <h1 className="lhead">{t("ghosts_headline")}</h1>
        <p className="lsub">{t("ghosts_sub")}</p>
        <div className="lcta">
          <button className="cta" onClick={onStart}>{t("cta_try")}</button>
          <a className="lghostbtn" href="#how">{t("cta_secondary")} ↓</a>
        </div>
        <p className="ltrust">🔒 {t("trust_line")}</p>
      </section>

      {/* 30-second visual tour (muted, captioned) */}
      <section className="lvideo reveal">
        <div className="vframe">
          <video src="/ad.mp4" muted autoPlay loop playsInline controls preload="metadata" />
        </div>
        <p className="vcap">▶ {t("video_caption")}</p>
      </section>

      {/* problem */}
      <section className="lband reveal">
        <span className="kick">{t("problem_kicker")}</span>
        <h2 className="bandtitle">{t("problem_title")}</h2>
        <p className="bandbody">{t("problem_body")}</p>
      </section>

      {/* how it works — illustrated, sound-optional */}
      <section id="how" className="lhow">
        <div className="howhead reveal">
          <span className="kick">{t("how_kicker")}</span>
          <h2 className="bandtitle">{t("how_title")}</h2>
          <p className="hsub">🔇 {t("how_sub")}</p>
        </div>
        <div className="lsteps">
          <Step n={1} icon={<PasteSVG />} title={t("step1_t")} desc={t("step1_d")} />
          <Step n={2} icon={<FormatSVG />} title={t("step2_t")} desc={t("step2_d")} />
          <Step n={3} icon={<DownloadSVG />} title={t("step3_t")} desc={t("step3_d")} />
          <Step n={4} icon={<OfflineSVG />} title={t("step4_t")} desc={t("step4_d")} />
        </div>
      </section>

      {/* accessibility */}
      <section className="laccess reveal">
        <div className="accicon" aria-hidden="true">👁️</div>
        <span className="kick">{t("access_kicker")}</span>
        <h2 className="bandtitle">{t("access_title")}</h2>
        <p className="bandbody">{t("access_body")}</p>
      </section>

      {/* use cases */}
      <section className="luses reveal">
        <h2 className="bandtitle center">{t("uses_title")}</h2>
        <div className="usegrid">
          <Use emoji="🎓" label={t("use_lectures")} />
          <Use emoji="✈️" label={t("use_flight")} />
          <Use emoji="💼" label={t("use_webinar")} />
          <Use emoji="🎧" label={t("use_podcast")} />
          <Use emoji="🔬" label={t("use_research")} />
          <Use emoji="🎬" label={t("use_backup")} />
        </div>
      </section>

      {/* privacy */}
      <section className="lband reveal">
        <span className="kick">🛡️</span>
        <h2 className="bandtitle">{t("privacy_title")}</h2>
        <p className="bandbody">{t("privacy_body")}</p>
      </section>

      {/* final CTA */}
      <section className="lfinal reveal">
        <h2 className="finaltitle">{t("final_title")}</h2>
        <button className="cta big" onClick={onStart}>{t("final_btn")} →</button>
        <p className="legal">{t("footer_legal")}</p>
      </section>
    </div>
  );
}
