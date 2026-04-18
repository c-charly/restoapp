<script setup lang="ts">
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { ref, reactive, useId } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const id = useId();
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const loading = ref(false)
const globalError = ref('')

function fillCred(email: string, password: string) {
  form.email = email
  form.password = password
}

async function handleLogin() {
  errors.email = ''; errors.password = ''; globalError.value = ''
  if (!form.email)    { errors.email = 'Email requis'; return }
  if (!form.password) { errors.password = 'Mot de passe requis'; return }

  loading.value = true
  try {
    await authStore.login(form.email, form.password)
    router.push({name: 'home'})
  } catch (e: any) {
    globalError.value = e.response?.data?.detail || 'Email ou mot de passe invalide'
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
    <Card class="relative z-1 w-full max-w-100">
      <CardContent>
        <div class="flex flex-col items-center gap-2">
          <div class="" aria-hidden="true">
            <img src="@/assets/logo.svg" alt="mon logo" class="h-8">
          </div>
          <CardHeader class="w-full">
            <CardTitle class="sm:text-center">Resto App</CardTitle>
            <CardDescription class="sm:text-center">
              Connectez-vous à votre espace
            </CardDescription>
          </CardHeader>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div class="space-y-4">
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-email`">Email</Label>
              <Input v-model="form.email" :id="`${id}-email`" placeholder="hi@restoapp.com" type="email" required />
              <span  :v-if="errors.email" class="text-[13px] text-red-500">{{ errors.email }}</span>
            </div>
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-password`">Mot de passe</Label>
              <Input v-model="form.password" :id="`${id}-password`" placeholder="Mot de passe" type="password" required />
              <span  :v-if="errors.password" class="text-[13px] text-red-500">{{ errors.password }}</span>
            </div>
          </div>

          <div class="mt-2">
            <p class="text-xs text-center p-2 w-full">Comptes de test</p>
            <div class="flex gap-2 items-center justify-center">
              <Button type="button" variant="outline" class="" @click="fillCred('alice@restoapp.cm', 'RestoPass!')">Client 1</button>
              <Button type="button" variant="outline" class="" @click="fillCred('bob@restoapp.cm', 'RestoPass!')">Client 2</button>
              <Button type="button" variant="outline" class="" @click="fillCred('admin@restoapp.cm', 'RestoPass!')">Admin</button>
            </div>
            </div>

          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading" class="animate-spin size-4 border border-white border-l-black rounded-[50%]"></span>
            {{ loading ? 'Connexion...' : 'Se connecter' }}
          </Button>

          <p class="text-[13px] opacity-50 text-center">
            Pas de compte ? <RouterLink to="/register">Créer un compte</RouterLink>
          </p>
        </form>

        <div v-if="globalError" class="mt-3 p-2 border border-destructive rounded-md bg-destructive/20 text-destructive">{{ globalError }}</div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.auth-bg {
  position: fixed; inset: 0; z-index: 0;
}
.grid-lines {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(var(--color-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-border) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.5;
}
.glow {
  position: absolute;
  width: 600px; height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 70%);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
}</style>
