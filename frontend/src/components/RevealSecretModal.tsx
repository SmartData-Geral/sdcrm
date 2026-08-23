import React, { useState } from "react";
import Modal from "./Modal";

interface RevealSecretModalProps {
  isOpen: boolean;
  title: string;
  secret: string;
  description?: string;
  onClose: () => void;
}

/**
 * Exibicao unica de um segredo recem-criado (chave de API ou segredo de webhook).
 *
 * O backend nao guarda o valor em texto puro -- so o hash, no caso da chave. Se o
 * usuario fechar sem copiar, o unico caminho e revogar e emitir outro. Por isso o
 * fechamento exige uma acao explicita, e nao ha como reabrir esta janela.
 */
const RevealSecretModal: React.FC<RevealSecretModalProps> = ({
  isOpen,
  title,
  secret,
  description,
  onClose,
}) => {
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
    } catch {
      // Sem permissao de clipboard: o valor segue selecionavel no campo.
      setCopiado(false);
    }
  };

  const fechar = () => {
    setCopiado(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} title={title} onClose={fechar}>
      <div className="reveal-secret">
        <div className="reveal-secret-warning" role="alert">
          <strong>Esta é a única vez que este valor será exibido.</strong>
          <p>
            {description ||
              "Copie agora e guarde em local seguro. O sistema não armazena o valor original — se você perdê-lo, será necessário revogar e emitir outro."}
          </p>
        </div>

        <label>
          Valor
          <input className="reveal-secret-input" readOnly value={secret} onFocus={(e) => e.target.select()} />
        </label>

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={() => void copiar()}>
            {copiado ? "Copiado ✔" : "Copiar"}
          </button>
          <button type="button" className="btn-primary" onClick={fechar}>
            Já copiei, fechar
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default RevealSecretModal;
