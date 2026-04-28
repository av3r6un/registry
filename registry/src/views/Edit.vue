<template>
  <article class="edit">
    <div class="edit_body section">
      <div class="edit_title">{{ editId ? $t('edit.edit_title') : $t('edit.create_title') }}</div>
      <form class="edit_form" @submit.prevent="submitDomain">
        <div class="form_row">
          <Input type="text" name="edit.form.domain" placeholder="example.com" required
            v-model="record.name"/>
          <Selection name="edit.form.proxy_type" v-model="proxyType" :options="proxyTypes" />
          <Input type="number" name="edit.form.port" placeholder="3000" required
            v-model="upstreamPort" v-if="!streamProxy"/>
          <Input type="number" name="edit.form.listen_port" placeholder="3000" required
            v-model="listenPort" v-else/>
        </div>
        <div class="form_row full" v-if="!streamProxy">
          <Input type="text" name="edit.form.aliases" placeholder="www.example.com, api.example.com"
            v-model="serverNames" />
        </div>
        <div class="form_row">
          <Input type="text" name="edit.form.upstream" placeholder="10.20.30.40" required
            v-model="record.route.upstream_host" />
          <Selection :options="actualScheme" name="edit.form.scheme" v-model="upstreamScheme" />
          <Input type="number" name="edit.form.upstream_port" placeholder="3000" required
            v-model="upstreamPort" v-if="streamProxy"/>
        </div>
        <div class="form_row" v-if="error">
          <p class="error">{{ error }}</p>
        </div>
        <div class="form_row">
          <button type="submit" class="btn btn_submit">{{ $t('edit.form.submit') }}</button>
          <router-link to="/" class="base_link btn_pure">{{ $t('edit.form.cancel') }}</router-link>
        </div>
      </form>
    </div>
  </article>
</template>
<script>
import Backend from '../services/backend.service';
import Input from '../components/Input.vue';
import Selection from '../components/Selection.vue';

export default {
  name: 'EditView',
  components: { Input, Selection },
  data() {
    return {
      backend: new Backend(),
      loading: false,
      error: null,
      record: {
        name: '',
        type: 'hostname',
        route: {
          listen_port: null,
          stream_protocol: '',
          upstream_host: '',
          upstream_port: null,
          upstream_scheme: 'http',
        },
        server_names: [],
      },
      proxyTypes: ['http', 'stream'],
      editId: this.$route.params.id,
    };
  },
  methods: {
    buildPayload() {
      const payload = { ...this.record };

      if (payload.type !== 'hostname') {
        delete payload.scheme;
        delete payload.server_names;
        return payload;
      }

      const aliases = String(payload.server_names || '')
        .split(/[\s,]+/)
        .map((name) => name.trim())
        .filter(Boolean);

      if (payload.domain && !aliases.includes(payload.domain)) {
        aliases.unshift(payload.domain);
      }

      payload.server_names = aliases;
      return payload;
    },
    async submitDomain() {
      if (this.editId) return this.updateDomain();
      this.loading = true;
      try {
        await this.backend.post('/domains', this.buildPayload())
        this.$router.push('/');
      } catch (err) {
        this.error = this.backend.msg;
      } finally {
        this.loading = false;
      }
    },
    async updateDomain() {
      this.loading = true;
      try {
        await this.backend.put(`/domains/${this.editId}`, this.buildPayload());
        this.$router.push('/');
      } catch (err) {
        this.error = this.backend.msg;
      } finally {
        this.loading = false;
      }
    },
    async fetchDomain() {
      this.loading = true;
      try {
        const resp = await this.backend.get(`/domains/${this.editId}`);
        const keys = Object.keys(this.record);
        keys.forEach((k) => {
          this.record[k] = resp[k];
        });
        if (Array.isArray(this.record.server_names)) {
          this.record.server_names = this.record.server_names.filter(Boolean);
        } else if (this.record.server_names) {
          this.record.server_names = String(this.record.server_names)
            .split(/[\s,]+/)
            .filter(Boolean);
        } else {
          this.record.server_names = [];
        }
      } catch (err) {
        this.error = this.backend.msg;
      } finally {
        this.loading = false;
      }
    },
  },
  computed: {
    upstreamPort: {
      get() { return this.record.route.upstream_port; },
      set(val) { this.record.route.upstream_port = Number(val); },
    },
    listenPort: {
      get() { return this.record.route.listen_port; },
      set(val) { this.record.route.listen_port = Number(val); },
    },
    actualScheme() {
      return this.record.type === 'hostname' ? ['http', 'https'] : ['tcp', 'udp'];
    },
    proxyType: {
      get() { return this.record.type === 'hostname' ? 'http' : 'stream'; },
      set(val) {
        this.record.type = val === 'stream' ? 'port_proxy' : 'hostname';
        if (this.record.type === 'hostname') {
          this.record.route.listen_port = null;
          if (!['http', 'https'].includes(this.record.route.upstream_scheme)) {
            this.record.route.upstream_scheme = 'http';
          }
        } else {
          this.record.route.upstream_scheme = 'stream';
          if (!['tcp', 'udp'].includes(this.record.route.stream_protocol)) {
            this.record.route.stream_protocol = 'tcp';
          }
        }
      },
    },
    serverNames: {
      get() { return this.record.server_names.join(', '); },
      set(val) { this.record.server_names = val.split(', '); },
    },
    upstreamScheme: {
      get() {
        return this.record.type === 'hostname' ? this.record.route.upstream_scheme : this.record.route.stream_protocol;
      },
      set(val) {
        if (this.record.type === 'hostname') {
          this.record.route.upstream_scheme = val;
        } else {
          this.record.route.stream_protocol = val;
        }
      },
    },
    streamProxy() {
      return this.record.type !== 'hostname';
    },
  },
  mounted() {
    if (this.editId) {
      this.fetchDomain();
    }
  },
};
</script>
<style lang="scss" scoped>
.edit{
  width: 100%;
  &_title{
    color: $white;
    font-size: 32px;
    margin-bottom: 20px;
  }
  &_form{
    display: flex;
    flex-direction: column;
    width: 100%;
    gap: 20px;
    .form_row{
      display: flex;
      width: 100%;
      gap: 15px;
      .error{
        color: red;
      }
    }
  }
}
</style>
