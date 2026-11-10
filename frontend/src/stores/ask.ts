import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { askQuestion } from "../services/api";
import type { Source } from "../types/api";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isError?: boolean;
}

export interface Conversation {
  id: number;
  title: string;
  messages: ChatMessage[];
}

export const useAskStore = defineStore("ask", () => {
  const conversations = ref<Conversation[]>([]);
  const activeId = ref<number | null>(null);
  const loading = ref(false);
  const pendingId = ref<number | null>(null);
  let nextId = 1;

  const active = computed(
    () => conversations.value.find((c) => c.id === activeId.value) ?? null,
  );

  function newChat() {
    activeId.value = null;
  }

  function select(id: number) {
    activeId.value = id;
  }

  async function ask(question: string, category: string | null) {
    let conversation = active.value;
    if (!conversation) {
      conversations.value.unshift({
        id: nextId++,
        title: question.length > 40 ? `${question.slice(0, 40)}…` : question,
        messages: [],
      });
      conversation = conversations.value[0];
      activeId.value = conversation.id;
    }
    conversation.messages.push({
      id: nextId++,
      role: "user",
      content: question,
    });
    loading.value = true;
    pendingId.value = conversation.id;
    try {
      const result = await askQuestion(question, category);
      conversation.messages.push({
        id: nextId++,
        role: "assistant",
        content: result.answer,
        sources: result.sources,
      });
    } catch (reason) {
      conversation.messages.push({
        id: nextId++,
        role: "assistant",
        content:
          reason instanceof Error ? reason.message : "Something went wrong.",
        isError: true,
      });
    } finally {
      loading.value = false;
      pendingId.value = null;
    }
  }

  return {
    conversations,
    activeId,
    active,
    loading,
    ask,
    newChat,
    select,
  };
});
