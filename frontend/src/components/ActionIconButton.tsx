import React from "react";

type IconKind = "view" | "edit" | "activate" | "deactivate" | "delete";

interface ActionIconButtonProps {
  icon: IconKind;
  label: string;
  onClick: () => void;
  tone?: "default" | "success" | "danger";
}

const iconPathMap: Record<IconKind, React.ReactNode> = {
  view: <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6zm10 3a3 3 0 100-6 3 3 0 000 6z" />,
  edit: <path d="M4 16.5V20h3.5L18.3 9.2l-3.5-3.5L4 16.5zm16.4-9.8a1 1 0 000-1.4l-1.5-1.5a1 1 0 00-1.4 0l-1.2 1.2 3.5 3.5 1.2-1.2z" />,
  activate: <path d="M12 2v3M6.3 4.7l2.1 2.1M2 12h3m1.3 5.3l2.1-2.1M12 19v3m5.7-4.7l-2.1-2.1M19 12h3m-4.3-7.3l-2.1 2.1M12 8a4 4 0 100 8 4 4 0 000-8z" />,
  deactivate: <path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 2a8 8 0 016.3 3.1L7.1 18.3A8 8 0 0112 4zm0 16a8 8 0 01-6.3-3.1L16.9 5.7A8 8 0 0112 20z" />,
  delete: <path d="M5 7h14M9 7V5h6v2m-8 0l1 12h8l1-12M10 11v6M14 11v6" />,
};

const ActionIconButton: React.FC<ActionIconButtonProps> = ({ icon, label, onClick, tone = "default" }) => {
  return (
    <button type="button" className={`icon-btn icon-btn--${tone}`} onClick={onClick} aria-label={label} title={label}>
      <svg viewBox="0 0 24 24" aria-hidden>
        {iconPathMap[icon]}
      </svg>
    </button>
  );
};

export default ActionIconButton;
