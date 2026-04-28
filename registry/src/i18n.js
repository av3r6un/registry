import { createI18n } from "vue-i18n";
import en from './locales/en.yaml';
import ru from './locales/ru.yaml';

export default createI18n({
  legacy: false,
  fallbackLocale: 'en',
  messages: { en, ru },
});
