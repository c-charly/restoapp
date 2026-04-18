<script setup lang="ts">
import { reactive, ref, useId } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '@/services/auth.service'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const id = useId()
const router = useRouter()

const form = reactive({
  email: '', password: '', first_name: '', last_name: '', phone: '', role: 'client'
})
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  error.value = ''
  if (!form.email || !form.password) { error.value = 'Email et mot de passe requis'; return }
  loading.value = true
  try {
    await authService.register(form)
    router.push({ name: 'login' })
  } catch (e: any) {
    const data = e.response?.data
    if (typeof data === 'object') {
      error.value = Object.values(data).flat().join(' ')
    } else {
      error.value = 'Une erreur est survenue'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
    <div class="auth-bg">
      <div class="grid-lines"></div>
      <div class="glow"></div>
    </div>
    <Card class="relative z-1 w-full max-w-[420px]">
      <CardContent>
        <div class="flex flex-col items-center gap-2">
          <img src="@/assets/logo.svg" alt="logo" class="h-8" />
          <CardHeader class="w-full">
            <CardTitle class="sm:text-center">Creer un compte</CardTitle>
            <CardDescription class="sm:text-center">Rejoignez Resto App</CardDescription>
          </CardHeader>
        </div>
        <form @submit.prevent="handleRegister" class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <Label :for="`${id}-first`">Prenom</Label>
              <Input v-model="form.first_name" :id="`${id}-first`" placeholder="Jean" />
            </div>
            <div class="space-y-1.5">
              <Label :for="`${id}-last`">Nom</Label>
              <Input v-model="form.last_name" :id="`${id}-last`" placeholder="Dupont" />
            </div>
          </div>
          <div class="space-y-1.5">
            <Label :for="`${id}-email`">Email *</Label>
            <Input v-model="form.email" :id="`${id}-email`" type="email" placeholder="jean@example.com" required />
          </div>
          <div class="space-y-1.5">
            <Label :for="`${id}-phone`">Telephone</Label>
            <Input v-model="form.phone" :id="`${id}-phone`" placeholder="+237 6XX XXX XXX" />
          </div>
          <div class="space-y-1.5">
            <Label :for="`${id}-password`">Mot de passe *</Label>
            <Input v-model="form.password" :id="`${id}-password`" type="password" placeholder="6 caracteres minimum" required />
          </div>

          <div v-if="error" class="p-2.5 border border-destructive rounded-md bg-destructive/10 text-destructive text-sm">
            {{ error }}
          </div>

          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading" class="animate-spin size-4 border border-white border-l-black rounded-[50%]"></span>
            {{ loading ? 'Création...' : 'Créer mon compte' }}
          </Button>
          <p class="text-[13px] opacity-50 text-center">
            Déjà un compte ? <RouterLink to="/login">Se connecter</RouterLink>
          </p>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.auth-bg { position: fixed; inset: 0; z-index: 0; }
.grid-lines {
  position: absolute; inset: 0;
  background-image: linear-gradient(var(--color-border) 1px, transparent 1px), linear-gradient(90deg, var(--color-border) 1px, transparent 1px);
  background-size: 40px 40px; opacity: 0.5;
}
.glow {
  position: absolute; width: 600px; height: 600px; border-radius: 50%;
  background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 70%);
  top: 50%; left: 50%; transform: translate(-50%, -50%);
}
</style>
