import api from './axios.service';

class Backend {
  msg = null;

  status = 'error';

  manageResp = ({ data }) => data.body;
  
  manageError = (err) => {
    const status = err?.response?.status;
    const statusText = err?.response?.statusText;
    const message = err?.response?.data?.error || err.message || 'request_failed';

    this.msg = status ? `${status} [${statusText}]: ${message}` : message;
    return Promise.reject(err);
  }

  async get(url, params) {
    return api
      .get(url, { params })
      .then((resp) => this.manageResp(resp))
      .catch((err) => this.manageError(err));
  }

  async post(url, body) {
    return api
      .post(url, body)
      .then((resp) => this.manageResp(resp))
      .catch((err) => this.manageError(err));
  }

  async put(url, body) {
    return api
      .put(url, body)
      .then((resp) => this.manageResp(resp))
      .catch((err) => this.manageError(err));
  }

  async delete(url) {
    return api
      .delete(url)
      .then((resp) => this.manageResp(resp))
      .catch((err) => this.manageError(err));
  }
}

export default Backend;
