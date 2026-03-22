import React from "react";

const svgProps = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const IcoSave = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
    <polyline points="17 21 17 13 7 13 7 21" />
    <polyline points="7 3 7 8 15 8" />
  </svg>
);

export const IcoPlus = () => (
  <svg {...svgProps} aria-hidden>
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

export const IcoFilePlus = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="12" y1="18" x2="12" y2="12" />
    <line x1="9" y1="15" x2="15" y2="15" />
  </svg>
);

export const IcoX = () => (
  <svg {...svgProps} aria-hidden>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export const IcoCheck = () => (
  <svg {...svgProps} aria-hidden>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export const IcoArrowLeft = () => (
  <svg {...svgProps} aria-hidden>
    <line x1="19" y1="12" x2="5" y2="12" />
    <polyline points="12 19 5 12 12 5" />
  </svg>
);

export const IcoSparkles = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M9.5 2.5l1 3.5 3.5 1-3.5 1-1 3.5-1-3.5-3.5-1 3.5-1z" />
    <path d="M19 11l.75 2.25L22 14l-2.25.75L19 17l-.75-2.25L16 14l2.25-.75z" />
  </svg>
);

export const IcoLayers = () => (
  <svg {...svgProps} aria-hidden>
    <polygon points="12 2 2 7 12 12 22 7 12 2" />
    <polyline points="2 17 12 22 22 17" />
    <polyline points="2 12 12 17 22 12" />
  </svg>
);

export const IcoMessage = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
  </svg>
);

export const IcoList = () => (
  <svg {...svgProps} aria-hidden>
    <line x1="8" y1="6" x2="21" y2="6" />
    <line x1="8" y1="12" x2="21" y2="12" />
    <line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" />
    <line x1="3" y1="12" x2="3.01" y2="12" />
    <line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);

export const IcoTrending = () => (
  <svg {...svgProps} aria-hidden>
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

export const IcoThermo = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M14 4v10.54a4 4 0 11-4 0V4a2 2 0 114 0z" />
  </svg>
);

export const IcoCheckCircle = () => (
  <svg {...svgProps} aria-hidden>
    <circle cx="12" cy="12" r="10" />
    <polyline points="8 12 11 15 16 9" />
  </svg>
);

export const IcoXCircle = () => (
  <svg {...svgProps} aria-hidden>
    <circle cx="12" cy="12" r="10" />
    <line x1="15" y1="9" x2="9" y2="15" />
    <line x1="9" y1="9" x2="15" y2="15" />
  </svg>
);

export const IcoPause = () => (
  <svg {...svgProps} aria-hidden>
    <rect x="6" y="4" width="4" height="16" />
    <rect x="14" y="4" width="4" height="16" />
  </svg>
);

export const IcoRotateCcw = () => (
  <svg {...svgProps} aria-hidden>
    <polyline points="1 4 1 10 7 10" />
    <path d="M3.51 15a9 9 0 102.13-9.36L1 10" />
  </svg>
);

export const IcoLink = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
  </svg>
);

export const IcoExternalLink = () => (
  <svg {...svgProps} aria-hidden>
    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

export const IcoPublish = () => (
  <svg {...svgProps} aria-hidden>
    <line x1="12" y1="19" x2="12" y2="5" />
    <polyline points="5 12 12 5 19 12" />
  </svg>
);

export const IcoSpinner = () => (
  <svg className="oportunidade-icon-btn__spinner" {...svgProps} aria-hidden>
    <path d="M12 2v4" opacity="0.9" />
    <path d="M12 18v4" opacity="0.15" />
    <path d="M4.93 4.93l2.83 2.83" opacity="0.25" />
    <path d="M16.24 16.24l2.83 2.83" opacity="0.35" />
    <path d="M2 12h4" opacity="0.45" />
    <path d="M18 12h4" opacity="0.55" />
    <path d="M4.93 19.07l2.83-2.83" opacity="0.65" />
    <path d="M16.24 7.76l2.83-2.83" opacity="0.75" />
  </svg>
);

type Variant = "ghost" | "subtle" | "outline-brand";

type Props = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  label: string;
  variant?: Variant;
  icon: React.ReactNode;
};

function cx(...parts: Array<string | false | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export const OportunidadeIconButton = React.forwardRef<HTMLButtonElement, Props>(
  ({ label, variant = "ghost", icon, className, type = "button", ...rest }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cx("oportunidade-icon-btn", `oportunidade-icon-btn--${variant}`, className)}
      aria-label={label}
      title={label}
      {...rest}
    >
      <span className="oportunidade-icon-btn__glyph">{icon}</span>
    </button>
  ),
);

OportunidadeIconButton.displayName = "OportunidadeIconButton";
