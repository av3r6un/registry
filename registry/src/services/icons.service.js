const req = require.context('!!raw-loader!@/assets/icons', false, /\.svg$/);

const icons = req.keys().reduce((acc, file) => {
  const name = file.replace('./', '').replace('.svg', '');
  acc[name] = req(file).default;
  return acc;
}, {});

export default icons;
