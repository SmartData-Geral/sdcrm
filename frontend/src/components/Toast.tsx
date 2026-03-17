import React, { useEffect } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

interface ToastProps {
  message: string;
  type?: ToastType;
  onClose: () => void;
  duration?: number;
}

const Toast: React.FC<ToastProps> = ({ message, type = "info", onClose, duration = 4000 }) => {
  useEffect(() => {
    const t = setTimeout(onClose, duration);
    return () => clearTimeout(t);
  }, [onClose, duration]);

  const icon =
    type === "success" ? "✔" : type === "error" ? "✕" : type === "warning" ? "⚠" : "ℹ";

  return (
    <div className={`toast toast--${type}`} role="alert">
      <span className="toast-icon">{icon}</span>
      <span className="toast-message">{message}</span>
    </div>
  );
};

export default Toast;

interface ToastContainerProps {
  toasts: Array<{ id: string; message: string; type?: ToastType }>;
  removeToast: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, removeToast }) => {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <Toast
          key={t.id}
          message={t.message}
          type={t.type}
          onClose={() => removeToast(t.id)}
        />
      ))}
    </div>
  );
};
