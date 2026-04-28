<template>
  <div class="domains section">
    <div class="domains_title">
      <span class="base_title">{{ $t('domains.title') }}</span>
      <div class="domains_actions">
        <button type="button" class="btn btn_clean" @click="$emit('refresh')"
          :disabled="loading">
          <mIcon name="refresh" />
        </button>
        <RouterLink to="/domains/new" class="base_link">
          <mIcon name="add-square" />
        </RouterLink>
      </div>
    </div>
    <div class="domains_body" v-if="loading">
      <LoadSpinner :state="loading" transparent primary="#4DA7FF" secondary="#3C86FF" class="ld"/>
    </div>
    <div class="domains_body" v-else>
      <table class="domains_table" v-if="localValue.length > 0">
        <thead>
          <tr class="domains_table-headers">
            <th class="domains_table-header s">{{ $t('domains.table.ssl') }}</th>
            <th class="domains_table-header n">{{ $t('domains.table.name') }}</th>
            <th class="domains_table-header l">{{ $t('domains.table.listen') }}</th>
            <th class="domains_table-header u">{{ $t('domains.table.upstream') }}</th>
            <th class="domains_table-header a">{{ $t('domains.table.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr class="domains_table-row row" v-for="d in localValue" :key="d.id">
            <td class="domains_table-data s">
                <mIcon :name="getProtectionIcon(d.ssl_enabled)" />
            </td>
            <td class="domains_table-data n">{{ d.name }}</td>
            <td class="domains_table-data l">{{ d.route.listen_port || 80 }}/{{ listenProtocol(d) }}</td>
            <td class="domains_table-data u">{{ d.route.upstream_host }}:{{ d.route.upstream_port }}</td>
            <td class="domains_table-data a">
              <button type="button" class="btn" @click="toggleRule(d.id)">
                <mIcon name="check" v-if="!d.enabled"/>
                <mIcon name="disable" v-else/>
              </button>
              <router-link :to="`/domains/${d.id}`">
                <mIcon name="view" />
              </router-link>
              <router-link :to="`/domains/edit/${d.id}`" class="base_link">
                <mIcon name="edit" />
              </router-link>
              <button type="button" class="btn" @click="deleteRule(d.id)">
                <mIcon name="delete" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else>There are no registered endpoints</p>
    </div>
  </div>
</template>
<script>
import mIcon from './materialIcon.vue';

export default {
  name: 'Domains',
  components: { mIcon },
  props: {
    modelValue: {
      type: Array,
      required: true,
    },
    loading: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {};
  },
  computed: {
    localValue: {
      get() { return this.modelValue; },
      set(val) { this.$emit('update:modelValue', val); },
    },
  },
  methods: {
    getProtectionIcon(state) {
      return state ? 'secured' : 'not-secured';
    },
    deleteRule(id) {
      this.$emit('action', 'delete', id);
    },
    toggleRule(id) {
      const state = this.localValue.find((d) => d.id === id)?.enabled;
      const action = state ? 'disable' : 'apply';
      this.$emit('action', action, id);
    },
    listenProtocol(domain) {
      return domain.type === 'hostname' ? domain.route.upstream_scheme : domain.route.stream_protocol;
    },
  },
};
</script>
<style lang="scss" scoped>
.domains{
  min-width: 920px;
  &_title{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }
  &_actions{
    display: flex;
    align-items: center;
    gap: 15px;
  }
  &_body{
    position: relative;
    display: flex;
    justify-content: center;
    &:has(table){
      display: block;
    }
    .ld{
      position: relative;
    }
  }
  &_table{
    border-collapse: separate;
    border-spacing: 10px 15px;
    &-headers{
      border-bottom: 15px;
    }
    &-header{
      color: $muted;
      font-weight: 300;
      font-size: 24px;
      text-align: left;
      padding: 0 10px
    }
    &-data{
      padding: 14px 10px;
      vertical-align: middle;
      font: $text-size $code-font;
      &.s{
        display: flex;
        justify-content: center;
        width: calc(100% - 20px);
      }
      &.a{
        display: flex;
        gap: 15px;
      }
    }
  }
}
</style>
