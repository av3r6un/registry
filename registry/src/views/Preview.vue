<template>
  <article class="preview" v-if="!error">
    <div class="preview_body section" v-if="loading">
      <LoadSpinner :state="loading" transparent primary="#4DA7FF" secondary="#3C86FF" class="ld"/>
    </div>
    <div class="preview_body section" v-else>
      <div class="preview_body-title">
        <div class="preview_body-rule">
          <div class="preview_body-name">{{ domain.name }}</div>
          <div class="preview_body-upstream">{{ upstream }}</div>
        </div>
        <div class="preview_body-actions">
          <router-link :to="`/domains/edit/${domain.id}`" class="base_link">
            <mIcon name="edit-property" />
          </router-link>
          <button type="button" class="btn" @click="enableSSL" v-if="onlyHttp">
            <mIcon name="add-protection" />
          </button>
          <button type="button" class="btn" @click="fetchDomain" :disabled="loading">
            <mIcon name="refresh" />
          </button>
        </div>
      </div>
      <div class="preview_body-info">
        <div class="preview_body-headers">
          <div class="preview_body-header s">{{ $t('domains.table.ssl') }}</div>
          <div class="preview_body-header a">{{ $t('domains.table.aliases') }}</div>
          <div class="preview_body-header t">{{ $t('domains.table.type') }}</div>
          <div class="preview_body-header c">{{ $t('domains.table.config_file') }}</div>
        </div>
        <div class="preview_body-content">
          <div class="preview_body-data s">
            <mIcon :name="protectedIcon" />
          </div>
          <div class="preview_body-data a">
            <div class="alias" v-for="(a, idx) in aliases" :key="idx">{{ a }}</div>
          </div>
          <div class="preview_body-data t">{{ domain.route.upstream_scheme }}</div>

          <div class="preview_body-data c">{{ domain.deployments[0].nginx_filename }}</div>
        </div>
      </div>
      <div class="preview_body-config">
        <div class="preview_body-title">{{ $t('domain.config.title') }}</div>
        <div class="preview_body-pre row">
          <pre class="config">{{ domain.deployments[0].config_text }}</pre>
        </div>
      </div>
    </div>
  </article>
  <article class="preview detailed_error" v-else>
    {{ error }}
  </article>
</template>
<script>
import Backend from '../services/backend.service';
import mIcon from '../components/materialIcon.vue';

export default {
  name: 'Preview',
  components: { mIcon },
  data() {
    return {
      backend: new Backend(),
      loading: true,
      error: null,
      domain: null,
    };
  },
  methods: {
    async fetchDomain() {
      this.loading = true;
      try {
        const resp = await this.backend.get(`/domains/${this.$route.params.id}`);
        this.domain = resp;
      } catch (err) {
        this.error = err;
      } finally {
        this.loading = false;
      }
    },
    async enableSSL() {
      this.loading = true;
      try {
        const resp = await this.backend.post(`/domains/${this.$route.params.id}/issue-certificate`)
        this.domain = resp;
      } catch (err) {
        this.error = this.backend.msg;
      } finally {
        this.loading = false;
      }
    },
  },
  computed: {
    protectedIcon() {
      return this.domain?.ssl_enabled ? 'secured' : 'not-secured';
    },
    aliases() {
      return this.domain?.server_names;
    },
    upstream() {
      return `${this.domain.route.upstream_scheme}://${this.domain.route.upstream_host}:${this.domain.route.upstream_port}`;
    },
    onlyHttp() {
      return this.domain.type === 'hostname' && !this.domain.certificates?.some((cert) => cert.status === 'active');
    },
  },
  beforeMount() {
    if (this.$route.params.id) {
      this.fetchDomain();
    } 
  },
};
</script>
<style lang="scss" scoped>
.preview{
  &_body{
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-width: 920px;
    .ld{
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    &-title{
      &:not(:has(.preview_body-rule)){
        font-size: 24px;
        font-weight: 300;
        margin-bottom: 20px;
        color: $muted;
      }
      &:has(.preview_body-rule){
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
    }
    &-actions{
      display: flex;
      align-items: center;
      gap: 15px;
    }
    &-rule{
      font-family: $code-font;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    &-name{
      font-size: 24px;
    }
    &-upstream{
      font-size: 14px;
      color: $muted;
    }
    &-info{
      display: table;
      border-spacing: 10px 15px;
      border-collapse: separate;
    }
    &-headers{
      display: table-row;
      font-size: 24px;
      font-weight: 300;
      color: $muted;
    }
    &-header{
      display: table-cell;
      vertical-align: middle;
    }
    &-content{
      display: table-row;
      border-radius: $radius-md;
      isolation: isolate;
      box-sizing: border-box;
      background: $row-bg;
      box-shadow: $glass-shadow;
    }
    &-data{
      &.s{
        padding: 14px 5px;
      }
      display: table-cell;
      vertical-align: middle;
      font-family: $code-font;
      padding: 14px 0;
    }
    &-pre{
      padding: 12px;
    }
  }
}
</style>
