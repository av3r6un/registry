<template>
  <div class="selection" v-click-outside="close">
    <div class="selection_name">{{ $t(name) }}</div>
    <div class="selection_selection input_wide" :class="{ opened, selected }" @click="toggle">
      <div class="selection_options" v-show="opened">
        <div class="selection_options-scroll">
          <div class="selection_option" v-for="(o, idx) in options" :key="idx">
            <div class="option" @click="select(o)">{{ o }}</div>
          </div>
        </div>
      </div>
      <div class="selection_default selected" v-if="selected">{{ localValue }}</div>
      <div class="selection_default" v-else>{{ $t(placeholder) }}</div>
    </div>
  </div>
</template>
<script>
export default {
  name: 'Selection',
  emits: ['update:modelValue'],
  props: {
    modelValue: {
      required: true,
    },
    options: {
      type: Array,
      required: true,
    },
    name: {
      type: String,
      required: true,
    },
    placeholder: {
      type: String,
      default: 'general.selection_placeholder',
    },
  },
  data() {
    return {
      opened: false,
    };
  },
  methods: {
    select(value) {
      this.localValue = value;
    },
    toggle() {
      this.opened = !this.opened;
    },
    close() {
      this.opened = false;
    },
    reset() {
      this.localValue = null;
    },
  },
  computed: {
    localValue: {
      get() { return this.modelValue },
      set(val) { this.$emit('update:modelValue', val)},
    },
    selected() {
      return this.modelValue !== '' && this.modelValue !== null;
    },
  },
};
</script>
<style lang="scss" scoped>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

.selection{
  &_name{
    margin-bottom: 5px;
    padding-left: 8px;
    font-weight: 400;
    font-family: $code-font;
  }
  &_selection{
    position: relative;
    user-select: none;
    min-width: 260px;
    cursor: pointer;
    &.opened{
      z-index: 2;
      .selection_default:after{
        transform: rotateX(180deg);
        top: calc(50% - 8px);
      }
    }
  }
  &_options{
    position: absolute;
    width: 100%;
    top: 100%;
    left: 0;
    margin-top: 5px;
    padding: 5px 10px;
    border-radius: 8px;
    background: rgba(#08111E, .5);
    backdrop-filter: blur(8px);
    border: $border;
    z-index: 1;
    box-sizing: border-box;
    &-scroll{
      max-height: 130px;
      overflow-y: auto;
      &::-webkit-scrollbar{
        display: none;
      }
    }
    .option{
      width: 100%;
      padding: 5px;
      box-sizing: border-box;
      border-radius: calc($radius-md / 1.5);
      font-size: 16px;
      cursor: pointer;
      &:hover{
        background: rgba($row-bg, .4);
        color: $white;
      }
    }
  }
  &_default{
    z-index: 1;
    display: flex;
    align-items: center;
    height: 100%;
    transition: all .4s ease;
    &:after{
      position: absolute;
      content: '\f078';
      font-family: 'FontAwesome';
      width: 16px;
      height: 16px;
      top: calc(50% - 9px);
      right: 12px;
      color: $white;
      transition: all .4s ease;
      z-index: 1;
    }
  }
}
</style>
