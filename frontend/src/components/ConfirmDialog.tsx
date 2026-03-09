import React from "react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title?: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ isOpen, title = "Confirmação", message, onConfirm, onCancel }) => {
  if (!isOpen) return null;
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <header className="modal-header">
          <h2>{title}</h2>
        </header>
        <div className="modal-body">
          <p>{message}</p>
          <div className="modal-actions">
            <button type="button" onClick={onCancel}>
              Cancelar
            </button>
            <button type="button" onClick={onConfirm} className="danger">
              Confirmar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;

