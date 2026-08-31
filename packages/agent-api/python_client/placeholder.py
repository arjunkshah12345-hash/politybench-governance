import { PolityEnv } from "./index";

export function make(scenario = "macro_fiscal_crisis", fidelity = "F2", seed = 41823) {
  return new PolityEnv(scenario, fidelity, seed);
}
