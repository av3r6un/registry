<template>
  <div class="home">
    <div class="home_records" v-if="error">
      {{ $t('main.load_failed') }}
    </div>
    <div class="home_records" v-else>
      <Domains v-model="domains" @refresh="fetchDomains" @action="manageAction"
        :loading="loading"/>
    </div>
  </div>
</template>

<script>
import Backend from '../services/backend.service';
import Domains from '../components/Domains.vue';

export default {
  name: 'IndexView',
  components: { Domains },
  data() {
    return {
      backend: new Backend(),
      loading: false,
      error: null,
      domains: [],
    };
  },
  methods: {
    async fetchDomains() {
      this.loading = true;
      try {
        this.domains = await this.backend.get('/domains');
      } catch (err) {
        this.error = err;
      } finally {
        this.loading = false;
      }
    },
    manageAction(action, id) {
      switch (action) {
        case "delete": return this.deleteRule(id);
        case "apply": return this.applyRule(id);
        default: return this.disableRule(id);
      }
    },
    async deleteRule(id) {
      this.loading = true;
      try {
        await this.backend.delete(`/domains/${id}`)
        const ruleIdx = this.domains.findIndex((d) => d.id === id);
        if (ruleIdx > -1) this.domains.splice(ruleIdx, 1);
      } catch (err) {
        this.error = err;
      } finally {
        this.loading = false;
      }
    },
    async applyRule(id) {
      this.loading = true;
      try {
        await this.backend.post(`/domains/${id}/apply`);
        const rule = this.domains.find((d) => d.id === id);
        if (rule) rule.enabled = 1;
      } catch (err) {
        this.error = err;
      } finally {
        this.loading = false;
      }
    },
    async disableRule(id) {
      this.loading = true;
      try {
        await this.backend.post(`/domains/${id}/disable`);
        const rule = this.domains.find((d) => d.id === id);
        if (rule) rule.enabled = 0;
      } catch (err) {
        this.error = err;
      } finally {
        this.loading = false;
      }
    }
  },
  beforeMount() {
    this.fetchDomains();
  },
};
</script>
<style lang="scss" scoped>
.home{
  &_records{
    display: flex;
    justify-content: center;
  }
}
</style>
