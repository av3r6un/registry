<template>
  <div class="m-icon"
    :style="{ width: `${w}px`, height: `${h}px`}"
    v-html="svg"
    @click="$emit('click')" />
</template>
<script>
import icons from '../services/icons.service';

export default {
  name: 'mIcon',
  props: {
    name: {
      type: String,
      required: true,
    },
    w: {
      type: [String, Number],
      default: 24,
    },
    h: {
      type: [String, Number],
      default: 24,
    },
  },
  computed: {
    svg() {
      const raw = icons[this.name];
      if (!raw) return '';
      return raw.replace(
        '<svg',
        `<svg width="${this.w}" height=${this.h}`,
      );
    }
  },
};
</script>
<style lang="scss"></style>
