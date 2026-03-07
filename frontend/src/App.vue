<template>
  <router-view />
</template>

<script setup>
// 根组件仅承载路由视图
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 200, 255, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 200, 255, 0.5);
}

/* Element Plus 暗黑主题覆盖 */
:root {
  --el-color-primary: #00d4ff;
  --el-color-primary-light-3: #33ddff;
  --el-color-primary-light-5: #66e5ff;
  --el-color-primary-light-7: #99eeff;
  --el-color-primary-light-8: #b3f1ff;
  --el-color-primary-light-9: #ccf5ff;
  --el-color-primary-dark-2: #00a8cc;
  --el-bg-color: #111827;
  --el-bg-color-overlay: #1f2937;
  --el-text-color-primary: #ffffff;
  --el-text-color-regular: rgba(255, 255, 255, 0.85);
  --el-text-color-secondary: rgba(255, 255, 255, 0.6);
  --el-border-color: rgba(0, 200, 255, 0.15);
  --el-border-color-light: rgba(0, 200, 255, 0.1);
  --el-fill-color-blank: rgba(17, 24, 39, 0.8);
}

/* 输入框 */
.el-input__wrapper {
  background-color: rgba(0, 0, 0, 0.3) !important;
  box-shadow: none !important;
  border: 1px solid rgba(0, 200, 255, 0.2) !important;
  transition: all 0.3s ease;
}

.el-input__wrapper:hover {
  border-color: rgba(0, 200, 255, 0.4) !important;
}

.el-input__wrapper.is-focus {
  border-color: #00d4ff !important;
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}

.el-input__inner {
  color: #fff !important;
}

.el-input__inner::placeholder {
  color: rgba(255, 255, 255, 0.3) !important;
}

/* 选择器 */
.el-select-dropdown {
  background: rgba(17, 24, 39, 0.95) !important;
  border: 1px solid rgba(0, 200, 255, 0.2) !important;
}

.el-select-dropdown__item {
  color: rgba(255, 255, 255, 0.85) !important;
}

.el-select-dropdown__item.hover,
.el-select-dropdown__item:hover {
  background: rgba(0, 200, 255, 0.1) !important;
}

.el-select-dropdown__item.selected {
  color: #00d4ff !important;
}

/* 按钮 */
.el-button--primary {
  background: linear-gradient(135deg, #00d4ff 0%, #0088ff 100%) !important;
  border: none !important;
}

.el-button--primary:hover {
  background: linear-gradient(135deg, #33ddff 0%, #0099ff 100%) !important;
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4) !important;
}

/* 标签 */
.el-tag {
  border: none !important;
}

/* 卡片 */
.el-card {
  background: rgba(17, 24, 39, 0.8) !important;
  border: 1px solid rgba(0, 200, 255, 0.15) !important;
  border-radius: 12px !important;
}

/* 表格 */
.el-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(0, 0, 0, 0.3);
  --el-table-row-hover-bg-color: rgba(0, 200, 255, 0.08);
  --el-table-border-color: rgba(0, 200, 255, 0.1);
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: rgba(255, 255, 255, 0.7);
}

/* 弹窗 */
.el-dialog {
  background: rgba(17, 24, 39, 0.95) !important;
  border: 1px solid rgba(0, 200, 255, 0.2) !important;
  border-radius: 16px !important;
}

.el-dialog__header {
  border-bottom: 1px solid rgba(0, 200, 255, 0.1) !important;
}

.el-dialog__title {
  color: #fff !important;
}

.el-dialog__body {
  color: rgba(255, 255, 255, 0.85) !important;
}

/* 分割线 */
.el-divider__text {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.6) !important;
  border-color: rgba(0, 200, 255, 0.1) !important;
}

/* 标签页 */
.el-tabs__item {
  color: rgba(255, 255, 255, 0.6) !important;
}

.el-tabs__item.is-active {
  color: #00d4ff !important;
}

.el-tabs__active-bar {
  background: #00d4ff !important;
}

/* 警告框 */
.el-alert {
  background: rgba(245, 158, 11, 0.1) !important;
  border: 1px solid rgba(245, 158, 11, 0.3) !important;
}

.el-alert__title {
  color: #f59e0b !important;
}

/* 空状态 */
.el-empty__description {
  color: rgba(255, 255, 255, 0.4) !important;
}

/* 描述列表 */
.el-descriptions__label {
  background: rgba(0, 0, 0, 0.2) !important;
  color: rgba(255, 255, 255, 0.6) !important;
  border-color: rgba(0, 200, 255, 0.1) !important;
}

.el-descriptions__content {
  background: rgba(0, 0, 0, 0.2) !important;
  color: #fff !important;
  border-color: rgba(0, 200, 255, 0.1) !important;
}

/* 开关 */
.el-switch.is-checked .el-switch__core {
  background: linear-gradient(135deg, #00d4ff, #0088ff) !important;
  border-color: #00d4ff !important;
}

/* 日期选择器 */
.el-picker-panel {
  background: rgba(17, 24, 39, 0.95) !important;
  border: 1px solid rgba(0, 200, 255, 0.2) !important;
}

.el-date-picker__header-label {
  color: #fff !important;
}

.el-picker-panel__icon-btn {
  color: rgba(255, 255, 255, 0.6) !important;
}

.el-date-table th {
  color: rgba(255, 255, 255, 0.6) !important;
}

.el-date-table td.today .el-date-table-cell__text {
  color: #00d4ff !important;
}

.el-date-table td.current .el-date-table-cell__text {
  background: linear-gradient(135deg, #00d4ff, #0088ff) !important;
}
</style>
