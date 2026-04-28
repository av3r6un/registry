<template>
  <div class="input">
    <div class="input_name">{{ $t(name) }}</div>
    <input
      :type="type"
      :required="required"
      :value="localValue"
      @input="(n) => localValue = n.target.value"
      :placeholder="placeholder"
      autocomplete="off"
      :min="min"
      :max="max"
      :step="step"
      class="input_wide">
  </div>
</template>
<script>
export default {
  name: 'Input',
  emits: ['update:modelValue'],
  model: {
    prop: 'modelValue',
    event: 'input',
  },
  props: {
    modelValue: {
      required: true,
    },
    type: {
      type: String,
      default: 'text',
    },
    required: {
      type: Boolean,
      default: false,
    },
    name: {
      type: String,
      required: true,
    },
    placeholder: {
      type: String,
      default: 'general.input_placeholder',
    },
    min: {
      type: String,
      default: '1',
    },
    max: {
      type: String,
    },
    step: {
      type: String,
      default: '1',
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
}
</script>
<style lang="scss" scoped>
.input{
  &_name{
    padding-left: 8px;
    margin-bottom: 5px;
    font-family: $code-font;
    font-weight: 400;
  }
}
</style>
