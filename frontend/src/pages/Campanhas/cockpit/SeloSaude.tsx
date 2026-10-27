import { ROTULO_SELO, type CockpitSelo } from "../metaAdsTipos";

export function SeloSaude({ selo }: { selo: CockpitSelo }) {
  return <span className={`cockpit-selo cockpit-selo--${selo}`}>{ROTULO_SELO[selo]}</span>;
}
