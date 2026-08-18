---
alwaysApply: false
description: 
---

HeroUI Rules

## 组件使用规范

### 1. Select 组件
  - 选择器组件用于选择多个选项中的一个，也可以多选。
  - 选项器组件的选项是通过 `options` 属性传递的。
  - 选项器组件的选项是通过 `value` 属性传递的, 而不是 `selectedKey` 属性。
  - 选择修改事件通过 `onChange` 属性传递，而不是 `onSelectionChange` 属性。