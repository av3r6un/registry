import { createApp } from 'vue';
import LoadSpinner from '@av3rgun/load-spinner';
import '@av3rgun/load-spinner/dist/load-spinner.css';
import App from './App.vue';
import router from './router';
import store from './store';
import '@/assets/main.scss';
import i18n from './i18n';

const app = createApp(App);
const clickOutsideHandlers = new WeakMap();

app.directive('click-outside', {
  beforeMount(el, binding) {
    const handler = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        if (typeof binding.value === 'function') {
          binding.value(event);
        }
      }
    };
    clickOutsideHandlers.set(el, handler);
    document.body.addEventListener('click', handler);
  },
  unmounted(el) {
    const handler = clickOutsideHandlers.get(el);
    if (handler) {
      document.body.removeEventListener('click', handler);
      clickOutsideHandlers.delete(el);
    }
  },
});

app
  .use(store)
  .use(router)
  .use(i18n)
  .use(LoadSpinner)
  .mount('#app');
