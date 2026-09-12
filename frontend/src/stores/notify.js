import { defineStore } from 'pinia'

let _id = 0

export const useNotifyStore = defineStore('notify', {
  state: () => ({
    items: [],
  }),
  actions: {
    push(type, message, ttl = 3000) {
      const id = ++_id
      this.items.push({ id, type, message })
      if (ttl > 0) {
        setTimeout(() => this.dismiss(id), ttl)
      }
      return id
    },
    success(msg, ttl) { return this.push('success', msg, ttl) },
    error(msg, ttl) { return this.push('error', msg, ttl ?? 4000) },
    info(msg, ttl) { return this.push('info', msg, ttl) },
    dismiss(id) {
      this.items = this.items.filter((n) => n.id !== id)
    },
  },
})
