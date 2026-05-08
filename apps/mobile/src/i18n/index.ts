// Minimal i18n scaffold: English ships at launch, Bahasa keys are populated
// from the prototype HTML's existing Bahasa copy and used as fallback.
//
// Default locale is `en` for v1 because the design handoff English copy is
// what's wired in screens; switch to `id` to render Bahasa.

import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import id from "./id.json";

i18next
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, id: { translation: id } },
    lng: "en",
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });

export { i18next };
