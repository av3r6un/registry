<template>
  <header class="header">
    <div class="header_title">Nginx Admin</div>
    <div class="header_subtitle">Registry</div>
  </header>
</template>
<script>
export default {
  name: 'Header',
};
</script>
<style lang="scss" scoped>
.header{
  text-align: center;
  &_title{
    font-family: $title-font;
    font-size: $title-size;
    text-shadow: $header-shadow;
  }
  &_subtitle{
    font-weight: 300;
    font-size: $subtitle-size;
    color: rgba($white, .5);
    text-shadow: $header-shadow;
  }
}
</style>
