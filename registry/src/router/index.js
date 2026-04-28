import { createRouter, createWebHistory } from 'vue-router';
import IndexView from '../views/Index.vue';
import Preview from '../views/Preview.vue';
import EditView from '../views/Edit.vue';

const routes = [
  {
    path: '/',
    name: 'index',
    component: IndexView
  },
  {
    path: '/domains/new',
    name: 'add',
    component: EditView,
  },
  {
    path: '/domains/:id',
    name: 'preview',
    component: Preview,
  },
  {
    path: '/domains/edit/:id',
    name: 'edit',
    component: EditView,
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
});

export default router;
