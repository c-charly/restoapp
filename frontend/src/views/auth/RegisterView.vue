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
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/auth.store'

const id = useId();
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ first_name: '', last_name: '', email: '', phone: '', password: '', role: 'client' })
const errors = reactive({ email: '', password: '' })
const loading = ref(false)
const globalError = ref('')
const success = ref(false)

async function handleRegister() {
  errors.email = ''; errors.password = ''; globalError.value = ''
  if (!form.email)    { errors.email = 'Email requis'; return }
  if (form.password.length < 6) { errors.password = 'Min. 6 caractères'; return }

  loading.value = true
  try {
    await authService.register(form)
    success.value = true
    await authStore.login(form.email, form.password)
    setTimeout(() => router.push('/'), 1200)
  } catch (e: any) {
    const d = e.response?.data
    if (d?.email) errors.email = d.email[0]
    else globalError.value = 'Erreur lors de la création du compte'
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
    <Card class="relative z-1 w-full max-w-[400px]">
      <CardContent>
        <div class="flex flex-col items-center gap-2">
          <div class="" aria-hidden="true">
            <img src="@/assets/logo.svg" alt="mon logo" class="h-8">
          </div>
          <CardHeader class="w-full">
            <CardTitle class="sm:text-center">Resto App</CardTitle>
            <CardDescription class="sm:text-center">
              Créer un nouveau compte
            </CardDescription>
          </CardHeader>
        </div>

        <form @submit.prevent="handleRegister" class="space-y-5">
          <div class="space-y-4">
            <div class="*:not-first:mt-2">
              <Label v-model="form.first_name" :for="`${id}-first-name`">First name</Label>
              <Input :id="`${id}-first-name`" placeholder="Toto" type="text" />
            </div>
            <!-- <div class="*:not-first:mt-2">
              <Label :for="`${id}-last-name`">Last name</Label>
              <Input v-model="form.last_name" :id="`${id}-last-name`" placeholder="Nvo" type="text" />
            </div> -->
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-email`">Email</Label>
              <Input v-model="form.email" :id="`${id}-email`" placeholder="hi@restoapp.com" type="email" required />
              <span  :v-if="errors.email" class="text-[13px] text-red-500">{{ errors.email }}</span>
            </div>
            <!-- <div class="*:not-first:mt-2">
              <Label :for="`${id}-phone`">Téléphone</Label>
              <Input v-model="form.phone" :id="`${id}-phone`" placeholder="237 000000000" type="tel" />
            </div> -->
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-password`">Mot de passe</Label>
              <Input v-model="form.password" :id="`${id}-password`" placeholder="Min. 6 caractères" type="password" required />
              <span  :v-if="errors.password" class="text-[13px] text-red-500">{{ errors.password }}</span>
            </div>
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading" class="animate-spin size-4 border border-white border-l-black rounded-[50%]"></span>
            {{ loading ? 'Création...' : "Créer le compte" }}
          </Button>

          <p class="text-[13px] opacity-50 text-center">Déjà un compte ? <RouterLink to="/login">Se connecter
            </RouterLink>
          </p>
        </form>

        <div v-if="globalError" class="mt-3 p-2 border border-destructive rounded-md bg-destructive/20 text-destructive">{{ globalError }}</div>
        <div v-if="success" class="mt-3 p-2 border border-accent rounded-md bg-accent/50 opacity-80">Compte créé ! Redirection...</div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.auth-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--color-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-border) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.5;
}

.glow {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.08) 0%, transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
