import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  validateStatus: (status) => status >= 200 && status < 400,
});

api.interceptors.request.use((config) => {
  config.headers.set('Accept', 'application/json');

  if (['post', 'put', 'patch'].includes(config.method)) {
    config.headers.set('Content-Type', 'application/json');
  }
  return config;
  },
  (err) => Promise.reject(err),
);

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err),
);

export default api;
