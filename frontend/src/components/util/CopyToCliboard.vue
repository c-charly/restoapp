<script setup lang="ts">
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Button
} from "@/components/ui/button";
import { useClipboard } from "@vueuse/core";
import { LucideCheck, LucideCopy } from "lucide-vue-next";

const props = defineProps<{
  value: string
}>()

const { copy, copied } = useClipboard();
</script>

<template>
  <div class="*:not-first:mt-2">
    <div class="px-1 py-0.5 border border-dashed rounded-md flex items-center gap-3">
      <span class="text-xs max-w-32 truncate">{{ value }}</span>
      <TooltipProvider>
        <Tooltip :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="sm" class="p-1.5"
              @click="copy(value)"
              :aria-label="copied ? 'super' : 'copier'"
              :disabled="copied"
            >
              <div
                :class="
                  cn('transition-all', copied ? 'scale-100 opacity-100' : 'scale-0 opacity-0')
                "
              >
                <LucideCheck class="stroke-emerald-700" :size="16" aria-hidden="true" />
              </div>
              <div
                :class="
                  cn(
                    'absolute transition-all',
                    copied ? 'scale-0 opacity-0' : 'scale-100 opacity-100',
                  )
                "
              >
                <LucideCopy :size="16" aria-hidden="true" />
              </div>
            </Button>
          </TooltipTrigger>
          <TooltipContent class="px-2 py-1 text-xs">copier dans la presse papier</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  </div>
</template>