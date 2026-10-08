import { useCallback, useEffect, useMemo, useState } from "react";

const emptyTransaction = () => ({
  type: "income",
  amount: "",
  category: "",
  description: "",
  date: new Date().toISOString().slice(0, 10),
});

const typeLabels = {
  income: "Нарахування",
  expense: "Списання",
};

const filters = [
  { value: "all", label: "Усі" },
  { value: "income", label: "Нарахування" },
  { value: "expense", label: "Списання" },
];

const couplePractices = [
  {
    id: "sensate-focus",
    icon: "🤲",
    label: "Дотик без мети",
    title: "Sensate Focus: дотик без мети",
    time: "40–50 хвилин",
    intro: "Практика, у якій важливі відчуття та цікавість, а не результат.",
    steps: [
      "Домовтеся про 40–50 хвилин і поділіть час приблизно порівну: по 15–20 хвилин на кожного.",
      "Торкайтеся рук, спини, плечей, шиї, обличчя чи живота — без сексуальних дій і без спроб досягти певного результату.",
      "Той або та, кого торкаються, може м’яко просити: «трохи ніжніше», «вище» або «повільніше».",
      "Наприкінці коротко обговоріть, що було приємним, несподіваним чи складним.",
    ],
  },
  {
    id: "emotion-and-need",
    icon: "💬",
    label: "Емоція й потреба",
    title: "Щоденний обмін емоцією й потребою",
    time: "5 хвилин",
    intro: "Маленький щоденний check-in, який допомагає чути одне одного без накопичення напруги.",
    steps: [
      "По черзі завершіть три фрази: «Я почуваюся…», «щодо…», «і мені зараз потрібно…».",
      "Обирайте будь-яку тему: це не обов’язково має бути конфлікт.",
      "Спробуйте зробити це за вечерею, на прогулянці або в короткому листуванні.",
      "Дайте партнеру простір вислухати, не виправляючи почуття та не поспішаючи з рішеннями.",
    ],
  },
  {
    id: "curious-assumptions",
    icon: "🔎",
    label: "Замість припущень",
    title: "Чи правильні мої припущення?",
    time: "10–15 хвилин",
    intro: "Вправа допомагає замінити здогадки про партнера уважною цікавістю.",
    steps: [
      "Кожен обирає одну конкретну ситуацію.",
      "Обережно сформулюйте здогад: «Коли сталося ___, я подумав/-ла, що ти відчував/-ла ___; це так?».",
      "Завдання іншого — уточнити свою відповідь, а не захищатися.",
      "Наприкінці назвіть одну річ, яку ви зрозуміли про досвід партнера трохи точніше.",
    ],
  },
  {
    id: "needs-map",
    icon: "🗺️",
    label: "Карта потреб",
    title: "Карта потреб у стосунках",
    time: "20 хвилин",
    intro: "Спосіб помітити, що саме зараз підтримує відчуття близькості для кожного з вас.",
    steps: [
      "Окремо випишіть п’ять важливих потреб у стосунках: наприклад, ніжність, час удвох, підтримку, легкість або більше ініціативи.",
      "Кожен обирає одну найактуальнішу потребу та пояснює: «Чому це важливо для мене зараз?».",
      "Партнер спершу лише слухає, а потім переповідає почуте своїми словами.",
      "Запитайте: «Який маленький крок міг би підтримати цю потребу цього тижня?».",
    ],
  },
  {
    id: "intimacy-space",
    icon: "🕯️",
    label: "Простір для близькості",
    title: "Плануйте не секс, а простір для близькості",
    time: "Раз на тиждень",
    intro: "Регулярна зустріч без побутових справ, телефонів і вимоги сексу.",
    steps: [
      "Раз на тиждень домовтеся про час для «інтимної зустрічі» без телефонів і справ.",
      "Оберіть те, що зараз відчувається природно: обійми, ванна, масаж, розмова, прогулянка чи дотики.",
      "Не ставте сексу обов’язковою метою цієї зустрічі.",
      "Після завершення скажіть одне одному, що допомогло відчути більше контакту.",
    ],
  },
];

const selfDiscoveryPractices = [
  {
    id: "object-projection",
    icon: "🪞",
    label: "Проекція на предмет",
    title: "Проекція на предмет",
    time: "15–20 хвилин",
    intro: "Образна практика для м’якого дослідження власного ставлення до сексуальності.",
    steps: [
      "Оберіть перший предмет, який привернув вашу увагу.",
      "Уявіть, що цей предмет — образ вашої сексуальності.",
      "Запитайте себе: яка вона, чого боїться, про що мріє та як із нею взаємодіють?",
      "Наприкінці сформулюйте, яке послання цей образ передає саме вам.",
    ],
  },
  {
    id: "sexual-words",
    icon: "✍️",
    label: "Сексуальні слова",
    title: "Сексуальні слова",
    time: "15 хвилин",
    intro: "Вправа, що допомагає помітити власні асоціації, напругу та заборони навколо теми сексуальності.",
    steps: [
      "Розділіть аркуш на три колонки: позитивні, нейтральні або суперечливі та негативні або заборонені асоціації.",
      "Запишіть слова й асоціації, що виникають у вас поруч зі словами «секс» і «сексуальність».",
      "Подивіться, яких слів найбільше та що повторюється.",
      "М’яко зауважте, біля яких слів з’являється напруга, сором або цікавість.",
    ],
  },
  {
    id: "letter-to-body",
    icon: "💌",
    label: "Лист своєму тілу",
    title: "Лист своєму тілу",
    time: "15–25 хвилин",
    intro: "Дбайливе письмове звернення до інтимної частини тіла як до живої частини себе.",
    steps: [
      "Напишіть лист до інтимної частини свого тіла так, ніби звертаєтеся до близької живої частини себе.",
      "Можете запитати: «Як ти почуваєшся?», «Коли я тебе не чую?», «Чого ти потребуєш від мене?».",
      "Дайте собі час записати відповідь без оцінювання та поспіху.",
      "Після листа зауважте, що виникло: тепло, сором, напруга, віддаленість чи щось інше.",
    ],
  },
  {
    id: "meeting-shame",
    icon: "🌧️",
    label: "Познайомитися зі соромом",
    title: "Познайомитися зі своїм соромом",
    time: "15–20 хвилин",
    intro: "Образна практика, що допомагає побачити сором без самозасудження.",
    steps: [
      "Намалюйте або опишіть свій сором як персонажа, образ чи істоту.",
      "Запитайте: «Від чого він мене захищає?».",
      "Подумайте, як цей голос міг би допомагати без самозасудження.",
      "Спробуйте перетворити його на уважність до власних меж, розбірливість або цікавість до себе.",
    ],
  },
  {
    id: "body-scan-breathing",
    icon: "🌿",
    label: "Сканування тіла з диханням",
    title: "Сканування тіла з диханням",
    time: "10–15 хвилин",
    intro: "Коротка практика заземлення та уважного контакту з тілесними відчуттями.",
    steps: [
      "Сядьте або ляжте зручно: одну руку покладіть на груди, іншу — на живіт.",
      "Зробіть 10 повільних циклів: вдих на 4 секунди, пауза на 2, видих на 6, пауза на 2.",
      "Після цього уважно проскануйте тіло від голови до стоп.",
      "Зауважте, де є тепло, напруга, порожнеча, легкість або бажання рухатися — без потреби щось змінювати.",
    ],
  },
];

const selfDiscoveryWarning = "Якщо під час будь-якої вправи з’являються сильний страх, біль або травматичні спогади, варто зупинитися й досліджувати це з психологом.";

const insightChatThreadStorageKey = "ai-insight-chat-thread";
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const currentView = new URLSearchParams(window.location.search).get("view");
const publicCabinetMode = currentView === "cabinet";
const adminMode = currentView === "admin";

async function fetchJson(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, { credentials: "include", ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = new Error(body?.detail || `API returned ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function formatDate(value) {
  return new Intl.DateTimeFormat("uk-UA", { dateStyle: "medium" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function formatCredits(value) {
  return new Intl.NumberFormat("uk-UA", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(Number(value));
}

export default function App() {
  const [accessPassword, setAccessPassword] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [accessError, setAccessError] = useState(null);
  const [authorizing, setAuthorizing] = useState(false);
  const [telegramIdInput, setTelegramIdInput] = useState("");
  const [selectedIdentity, setSelectedIdentity] = useState(null);
  const [identityError, setIdentityError] = useState(null);
  const [selectingIdentity, setSelectingIdentity] = useState(false);
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState(emptyTransaction);
  const [formOpen, setFormOpen] = useState(false);
  const [filter, setFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [insightChatMessages, setInsightChatMessages] = useState([]);
  const [insightChatInput, setInsightChatInput] = useState("");
  const [insightChatLoading, setInsightChatLoading] = useState(false);
  const [insightChatError, setInsightChatError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [actionProcessing, setActionProcessing] = useState(false);
  const [pendingActionError, setPendingActionError] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isPracticesOpen, setIsPracticesOpen] = useState(false);
  const [practiceCollection, setPracticeCollection] = useState("couple");
  const [selectedPractice, setSelectedPractice] = useState(null);
  const [practiceLibrary, setPracticeLibrary] = useState(null);
  const [isPublicPracticesOpen, setIsPublicPracticesOpen] = useState(false);
  const [practiceToOpen, setPracticeToOpen] = useState(null);
  const [openedPractice, setOpenedPractice] = useState(null);
  const [practiceOpeningId, setPracticeOpeningId] = useState(null);
  const [practicePurchaseError, setPracticePurchaseError] = useState(null);
  const [adminPracticeLibrary, setAdminPracticeLibrary] = useState(null);
  const [adminPracticeOpeningId, setAdminPracticeOpeningId] = useState(null);
  const [adminPracticeError, setAdminPracticeError] = useState(null);
  const [telegramUser, setTelegramUser] = useState(null);
  const [telegramAuthError, setTelegramAuthError] = useState(null);
  const [telegramAuthLoading, setTelegramAuthLoading] = useState(publicCabinetMode);
  const [insightChatThreadId, setInsightChatThreadId] = useState(
    () => window.sessionStorage.getItem(insightChatThreadStorageKey) || "",
  );

  const loadPracticeLibrary = useCallback(async () => {
    const library = await fetchJson("/api/me/practices");
    setPracticeLibrary(library);
  }, []);

  useEffect(() => {
    if (!publicCabinetMode) {
      return;
    }
    const webApp = window.Telegram?.WebApp;
    if (!webApp?.initData) {
      setTelegramAuthError("Відкрийте особистий кабінет кнопкою в Telegram-боті Intima.");
      setTelegramAuthLoading(false);
      return;
    }

    webApp.ready();
    webApp.expand();
    fetchJson("/api/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: webApp.initData }),
    })
      .then(async (user) => {
        setTelegramUser(user);
        try {
          await loadPracticeLibrary();
        } catch {
          setPracticePurchaseError("Не вдалося завантажити добірку практик. Спробуйте ще раз.");
        }
      })
      .catch(() => setTelegramAuthError("Не вдалося безпечно підтвердити Telegram-профіль. Відкрийте кабінет ще раз через бота."))
      .finally(() => setTelegramAuthLoading(false));
  }, [loadPracticeLibrary]);

  useEffect(() => {
    if (!isPracticesOpen && !isPublicPracticesOpen) {
      return undefined;
    }
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setIsPracticesOpen(false);
        setSelectedPractice(null);
        setIsPublicPracticesOpen(false);
        setPracticeToOpen(null);
        setOpenedPractice(null);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isPracticesOpen, isPublicPracticesOpen]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const identityQuery = selectedIdentity ? `?telegram_id=${encodeURIComponent(selectedIdentity.telegram_id)}` : "";
      const [summaryData, transactionData] = await Promise.all([
        fetchJson(`/api/summary${identityQuery}`, { headers: { "X-Admin-Password": accessPassword } }),
        fetchJson(`/api/transactions${identityQuery}`, { headers: { "X-Admin-Password": accessPassword } }),
      ]);
      setSummary(summaryData);
      setTransactions(transactionData);
    } catch {
      setError(
        "Не вдалося отримати дані. Переконайтеся, що FastAPI працює на порту 8000.",
      );
    } finally {
      setLoading(false);
    }
  }, [accessPassword, selectedIdentity]);

  useEffect(() => {
    if (accessPassword) {
      loadDashboard();
    } else {
      setLoading(false);
    }
  }, [accessPassword, loadDashboard]);

  const loadAdminPracticeLibrary = useCallback(async (identity) => {
    if (!identity || !accessPassword) {
      setAdminPracticeLibrary(null);
      return null;
    }
    const library = await fetchJson(
      `/api/admin/identities/telegram/${identity.telegram_id}/practices`,
      { headers: { "X-Admin-Password": accessPassword } },
    );
    setAdminPracticeLibrary(library);
    return library;
  }, [accessPassword]);

  const categories = useMemo(
    () => [...new Set(transactions.map((transaction) => transaction.category))].sort(),
    [transactions],
  );

  const visibleTransactions = useMemo(
    () => transactions.filter((transaction) => (
      (filter === "all" || transaction.type === filter)
      && (categoryFilter === "all" || transaction.category === categoryFilter)
    )),
    [categoryFilter, filter, transactions],
  );

  const expenseStructure = useMemo(() => {
    const categoriesWithExpenses = new Map();
    for (const transaction of transactions) {
      if (transaction.type !== "expense") {
        continue;
      }
      categoriesWithExpenses.set(
        transaction.category,
        (categoriesWithExpenses.get(transaction.category) || 0) + Number(transaction.amount),
      );
    }

    const total = [...categoriesWithExpenses.values()].reduce((sum, amount) => sum + amount, 0);
    return [...categoriesWithExpenses.entries()]
      .map(([category, amount]) => ({ category, amount, share: total ? (amount / total) * 100 : 0 }))
      .sort((first, second) => second.amount - first.amount);
  }, [transactions]);

  const cards = [
    { label: "Нараховано", value: summary?.total_income ?? 0, icon: "✨" },
    { label: "Списано", value: summary?.total_expense ?? 0, icon: "🌿" },
    { label: "Баланс кредитів", value: summary?.balance ?? 0, icon: "💜" },
  ];
  const selectedAdminPractice = selectedPractice
    ? adminPracticeLibrary?.practices.find((practice) => practice.id === selectedPractice.id)
    : null;
  const activeAdminPractices = practiceCollection === "self" ? selfDiscoveryPractices : couplePractices;
  const activePracticeTitle = practiceCollection === "self" ? "Практики для самопізнання" : "Практики для двох";

  async function handleAccess(event) {
    event.preventDefault();
    if (!passwordInput) {
      setAccessError("Введіть пароль адміністратора.");
      return;
    }

    setAuthorizing(true);
    setAccessError(null);
    try {
      await fetchJson("/api/admin/access", {
        method: "POST",
        headers: { "X-Admin-Password": passwordInput },
      });
      setAccessPassword(passwordInput);
      setPasswordInput("");
    } catch (requestError) {
      setAccessError(requestError.message || "Не вдалося перевірити пароль.");
    } finally {
      setAuthorizing(false);
    }
  }

  async function handleIdentitySelection(event) {
    event.preventDefault();
    const telegramId = telegramIdInput.trim();
    if (!/^\d+$/.test(telegramId) || Number(telegramId) <= 0) {
      setIdentityError("Введіть коректний числовий Telegram ID.");
      return;
    }
    setSelectingIdentity(true);
    setIdentityError(null);
    try {
      const identity = await fetchJson(`/api/identities/telegram/${telegramId}`, {
        headers: { "X-Admin-Password": accessPassword },
      });
      setSelectedIdentity(identity);
      await loadAdminPracticeLibrary(identity);
      setInsightChatThreadId("");
      setInsightChatMessages([]);
      setPendingAction(null);
    } catch (requestError) {
      setIdentityError(requestError.message || "Не вдалося знайти профіль.");
    } finally {
      setSelectingIdentity(false);
    }
  }

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function openPractices(collection = "couple") {
    setPracticeCollection(collection);
    setSelectedPractice(null);
    setIsPracticesOpen(true);
  }

  function closePractices() {
    setIsPracticesOpen(false);
    setSelectedPractice(null);
  }

  function closePublicPractices() {
    setIsPublicPracticesOpen(false);
    setPracticeToOpen(null);
    setOpenedPractice(null);
    setPracticePurchaseError(null);
  }

  async function openPublicPractice(practice) {
    setPracticeOpeningId(practice.id);
    setPracticePurchaseError(null);
    try {
      const content = await fetchJson(`/api/me/practices/${practice.id}/open`, { method: "POST" });
      setOpenedPractice(content);
      setPracticeToOpen(null);
      await loadPracticeLibrary();
    } catch (requestError) {
      setPracticePurchaseError(
        requestError.message || "Не вдалося відкрити практику. Спробуйте ще раз.",
      );
    } finally {
      setPracticeOpeningId(null);
    }
  }

  async function openAdminPractice(practice) {
    if (!selectedIdentity || adminPracticeOpeningId) {
      return;
    }
    setAdminPracticeOpeningId(practice.id);
    setAdminPracticeError(null);
    try {
      await fetchJson(
        `/api/admin/identities/telegram/${selectedIdentity.telegram_id}/practices/${practice.id}/open`,
        {
          method: "POST",
          headers: { "X-Admin-Password": accessPassword },
        },
      );
      await Promise.all([loadDashboard(), loadAdminPracticeLibrary(selectedIdentity)]);
    } catch (requestError) {
      setAdminPracticeError(
        requestError.message || "Не вдалося відкрити практику для цього профілю.",
      );
    } finally {
      setAdminPracticeOpeningId(null);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const amount = Number(form.amount);

    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError("Вкажіть суму кредитів, більшу за нуль.");
      return;
    }
    if (!form.category.trim()) {
      setFormError("Вкажіть категорію операції.");
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      await fetchJson("/api/transactions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": accessPassword,
        },
        body: JSON.stringify({ ...form, amount, telegram_id: selectedIdentity?.telegram_id }),
      });
      setForm(emptyTransaction());
      setFormOpen(false);
      await loadDashboard();
    } catch (requestError) {
      setFormError(
        requestError.message || "Не вдалося зберегти операцію. Спробуйте ще раз.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(transaction) {
    if (!window.confirm("Видалити операцію?")) {
      return;
    }

    setDeletingId(transaction.id);
    setError(null);
    try {
      const identityQuery = selectedIdentity ? `?telegram_id=${selectedIdentity.telegram_id}` : "";
      await fetchJson(`/api/transactions/${transaction.id}${identityQuery}`, {
        method: "DELETE",
        headers: { "X-Admin-Password": accessPassword },
      });
      await loadDashboard();
    } catch {
      setError("Не вдалося видалити операцію. Спробуйте ще раз.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleInsightChatSubmit(event) {
    event.preventDefault();
    const message = insightChatInput.trim();
    if (!message || insightChatLoading) {
      return;
    }

    setInsightChatMessages((current) => [...current, { role: "user", content: message }]);
    setInsightChatInput("");
    setInsightChatError(null);
    setInsightChatLoading(true);
    try {
      const result = await fetchJson("/api/ai/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": accessPassword,
        },
        body: JSON.stringify({
          message,
          telegram_id: selectedIdentity?.telegram_id,
          thread_id: insightChatThreadId || undefined,
        }),
      });
      setInsightChatThreadId(result.thread_id);
      window.sessionStorage.setItem(insightChatThreadStorageKey, result.thread_id);
      setInsightChatMessages((current) => [...current, { role: "assistant", content: result.answer }]);
      if (result.pending_action) {
        setPendingAction(result.pending_action);
        setPendingActionError(null);
        setIsChatOpen(true);
      }
    } catch (error) {
      setInsightChatError(
        error?.status === 429
          ? error.message
          : "Не вдалося отримати відповідь AI INSIGHT. Спробуйте ще раз трохи пізніше.",
      );
    } finally {
      setInsightChatLoading(false);
    }
  }

  function startNewInsightChat() {
    window.sessionStorage.removeItem(insightChatThreadStorageKey);
    setInsightChatThreadId("");
    setInsightChatMessages([]);
    setInsightChatInput("");
    setInsightChatError(null);
  }

  async function handleConfirmPendingAction() {
    if (!pendingAction || actionProcessing) {
      return;
    }

    setActionProcessing(true);
    setPendingActionError(null);
    try {
      const result = await fetchJson(`/api/ai/actions/${pendingAction.id}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": accessPassword },
        body: JSON.stringify({ telegram_id: selectedIdentity?.telegram_id }),
      });
      setPendingAction(null);
      setInsightChatMessages((current) => [
        ...current,
        { role: "assistant", content: "✅ Дію підтверджено. Ledger кредитів оновлено." },
      ]);
      await loadDashboard();
      return result;
    } catch (requestError) {
      setPendingActionError(
        requestError.message || "Не вдалося підтвердити запропоновану дію.",
      );
    } finally {
      setActionProcessing(false);
    }
  }

  async function handleCancelPendingAction() {
    if (!pendingAction || actionProcessing) {
      return;
    }

    setActionProcessing(true);
    setPendingActionError(null);
    try {
      await fetchJson(`/api/ai/actions/${pendingAction.id}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": accessPassword },
        body: JSON.stringify({ telegram_id: selectedIdentity?.telegram_id }),
      });
      setPendingAction(null);
      setInsightChatMessages((current) => [
        ...current,
        { role: "assistant", content: "Дію скасовано. Ledger кредитів не змінювався." },
      ]);
    } catch (requestError) {
      setPendingActionError(
        requestError.message || "Не вдалося скасувати запропоновану дію.",
      );
    } finally {
      setActionProcessing(false);
    }
  }

  async function handleTelegramLogout() {
    await fetchJson("/api/auth/logout", { method: "POST" }).catch(() => null);
    window.Telegram?.WebApp?.close();
  }

  if (publicCabinetMode) {
    return (
      <main className="public-cabinet">
        <section className="public-cabinet-card">
          <p className="eyebrow">INTIMA · ОСОБИСТИЙ КАБІНЕТ</p>
          <span className="cabinet-flower" aria-hidden="true">🌿</span>
          <h1>Простір для близькості</h1>
          {telegramAuthLoading && <p className="subtitle">Безпечно підтверджуємо ваш Telegram-профіль…</p>}
          {telegramAuthError && <p className="form-error" role="alert">{telegramAuthError}</p>}
          {telegramUser && (
            <>
              <p className="subtitle">
                Вітаємо, {telegramUser.first_name || telegramUser.username || "друже"}. Ваш профіль Intima підтверджено через Telegram.
              </p>
              <div className="cabinet-next-steps">
                <p>Оберіть одну з м’яких практик для близькості. Кожна нова практика відкривається за 1 кредит Intima.</p>
                <p>Ми не показуємо чужі дані й не просимо вводити Telegram ID вручну.</p>
              </div>
              <section className="cabinet-practices" aria-labelledby="cabinet-practices-heading">
                <div>
                  <p className="eyebrow">ПРАКТИКИ INTIMA</p>
                  <h2 id="cabinet-practices-heading">Ваш баланс: {formatCredits(practiceLibrary?.balance ?? 0)} кредитів</h2>
                </div>
                <button className="cabinet-practices-button" disabled={!practiceLibrary} onClick={() => setIsPublicPracticesOpen(true)} type="button">
                  {practiceLibrary ? "Обрати практику" : "Завантажуємо…"}
                </button>
              </section>
              {practicePurchaseError && <p className="form-error" role="alert">{practicePurchaseError}</p>}
              <button className="logout-button" onClick={handleTelegramLogout} type="button">Закрити кабінет</button>
            </>
          )}
        </section>

        {isPublicPracticesOpen && (
          <div className="practices-overlay" onMouseDown={closePublicPractices} role="presentation">
            <section
              aria-labelledby="public-practices-heading"
              aria-modal="true"
              className="practices-modal public-practices-modal"
              onMouseDown={(event) => event.stopPropagation()}
              role="dialog"
            >
              <button aria-label="Закрити практики" className="modal-close-button" onClick={closePublicPractices} type="button">×</button>
              {openedPractice ? (
                <>
                  <button className="back-to-practices" onClick={() => setOpenedPractice(null)} type="button">← До добірки</button>
                  <div className="practice-detail-heading">
                    <span aria-hidden="true">{openedPractice.icon}</span>
                    <div>
                      <p className="eyebrow">{openedPractice.time} · ВІДКРИТО</p>
                      <h2 id="public-practices-heading">{openedPractice.title}</h2>
                    </div>
                  </div>
                  <p className="practices-intro">{openedPractice.intro}</p>
                  <ol className="practice-steps">
                    {openedPractice.steps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                  <p className="practice-note">💜 {openedPractice.collection === "self" ? "Обирайте лише те, що комфортно вам. Можна зупинитися, змінити темп або відкласти вправу в будь-який момент." : "Обирайте лише те, що комфортно вам обом. Можна зупинитися, змінити темп або відкласти вправу в будь-який момент."}</p>
                  {openedPractice.warning && <p className="practice-warning">⚠️ {openedPractice.warning}</p>}
                </>
              ) : practiceToOpen ? (
                <>
                  <button className="back-to-practices" disabled={Boolean(practiceOpeningId)} onClick={() => setPracticeToOpen(null)} type="button">← До добірки</button>
                  <span className="purchase-practice-icon" aria-hidden="true">{practiceToOpen.icon}</span>
                  <p className="eyebrow">ПІДТВЕРДЖЕННЯ ВІДКРИТТЯ</p>
                  <h2 id="public-practices-heading">Відкрити «{practiceToOpen.label}»?</h2>
                  <p className="practices-intro">З вашого балансу буде списано 1 кредит Intima. Після цього практика залишиться доступною для вас без повторної оплати.</p>
                  {practiceToOpen.collection === "self" && <p className="practice-warning">⚠️ {selfDiscoveryWarning}</p>}
                  {practicePurchaseError && <p className="form-error" role="alert">{practicePurchaseError}</p>}
                  <div className="practice-purchase-actions">
                    <button className="purchase-confirm-button" disabled={Boolean(practiceOpeningId)} onClick={() => openPublicPractice(practiceToOpen)} type="button">
                      {practiceOpeningId ? "Відкриваємо…" : "Відкрити за 1 кредит"}
                    </button>
                    <button className="purchase-cancel-button" disabled={Boolean(practiceOpeningId)} onClick={() => setPracticeToOpen(null)} type="button">Не зараз</button>
                  </div>
                </>
              ) : (
                <>
                  <p className="eyebrow">INTIMA · ПРАКТИКИ</p>
                  <h2 id="public-practices-heading">Оберіть практику</h2>
                  <p className="practices-intro">Нову практику можна відкрити за 1 кредит. Уже відкриті практики залишаться з вами.</p>
                  {[
                    { id: "couple", label: "Для вас двох" },
                    { id: "self", label: "Для самопізнання" },
                  ].map((group) => (
                    <section className="public-practice-group" key={group.id}>
                      <p className="eyebrow">{group.label}</p>
                      <div className="practice-choice-grid">
                        {practiceLibrary?.practices.filter((practice) => practice.collection === group.id).map((practice) => (
                          <button className="practice-choice" disabled={practiceOpeningId === practice.id} key={practice.id} onClick={() => (
                            practice.unlocked ? openPublicPractice(practice) : setPracticeToOpen(practice)
                          )} type="button">
                            <span aria-hidden="true">{practice.icon}</span>
                            <strong>{practice.label}</strong>
                            <small>{practice.unlocked ? "✓ Уже відкрито" : "1 кредит · "}{practice.time}</small>
                          </button>
                        ))}
                      </div>
                    </section>
                  ))}
                </>
              )}
            </section>
          </div>
        )}
      </main>
    );
  }

  if (!adminMode) {
    return (
      <main className="public-cabinet">
        <section className="public-cabinet-card">
          <p className="eyebrow">INTIMA · ПРОСТІР ТУРБОТИ</p>
          <span className="cabinet-flower" aria-hidden="true">♥</span>
          <h1>Самопізнання та близькість у власному темпі</h1>
          <p className="subtitle">
            Intima допомагає досліджувати контакт із собою та будувати тепліші взаємодії в парі через м’які практики.
          </p>
          <div className="cabinet-next-steps">
            <p><strong>♡ Практики для двох</strong> — вправи для діалогу, дотиків і спільного часу.</p>
            <p><strong>✦ Самопізнання</strong> — уважні практики для контакту з тілом, потребами й почуттями.</p>
            <p>Щоб відкрити особистий кабінет і користуватися кредитами, перейдіть сюди кнопкою з Telegram-бота Intima.</p>
          </div>
          <a
            className="telegram-entry-button"
            href="https://t.me/IntimaCoupleBot"
            rel="noreferrer"
            target="_blank"
          >
            ✈ Відкрити Intima у Telegram
          </a>
        </section>
      </main>
    );
  }

  if (!accessPassword) {
    return (
      <main className="access-screen">
        <section className="access-card">
          <p className="eyebrow">INTIMA · ADMIN</p>
          <h1>Кредити Intima</h1>
          <p className="subtitle">Введіть локальний пароль адміністратора, щоб відкрити ledger кредитів.</p>
          <form className="access-form" onSubmit={handleAccess}>
            <label>
              Пароль адміністратора
              <input
                autoComplete="current-password"
                onChange={(event) => setPasswordInput(event.target.value)}
                type="password"
                value={passwordInput}
              />
            </label>
            {accessError && <p className="form-error" role="alert">{accessError}</p>}
            <button className="submit-button" disabled={authorizing} type="submit">
              {authorizing ? "Перевіряємо…" : "Відкрити адмінку"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <header className="hero">
        <div className="brand-block">
          <p className="eyebrow">INTIMA · ADMIN</p>
          <h1>Сервіс Intima <span className="title-heart">♥</span></h1>
          <p className="subtitle">
            Кредити, взаємодії та корисні сервіси для самопізнання та близькості у парі.
          </p>
        </div>
        <div className="admin-controls">
          <div className="system-actions">
            <button className="logout-button" onClick={() => {
              setAccessPassword("");
              setSelectedIdentity(null);
              setTelegramIdInput("");
              setAdminPracticeLibrary(null);
            }}>Вийти</button>
            <button className="refresh-button" onClick={loadDashboard} disabled={loading}>
              {loading ? "Оновлюємо…" : "Оновити"}
            </button>
          </div>
          <form className="identity-picker" onSubmit={handleIdentitySelection}>
            <label>
              <span>Telegram ID</span>
              <input
                inputMode="numeric"
                onChange={(event) => setTelegramIdInput(event.target.value)}
                placeholder="ID користувача"
                value={telegramIdInput}
              />
            </label>
            <button className="identity-submit" disabled={selectingIdentity} type="submit">
              {selectingIdentity ? "Шукаємо…" : "Показати"}
            </button>
          </form>
        </div>
        <div className="functional-actions" aria-label="Функції Intima">
          <button className="practices-trigger" onClick={() => openPractices("couple")} type="button">
            ♡ Практики для двох
          </button>
          <button className="practices-trigger self-practices-trigger" onClick={() => openPractices("self")} type="button">
            ✦ Самопізнання
          </button>
          <button className="add-operation-button" onClick={() => setFormOpen(true)} type="button">
            ＋ Додати операцію
          </button>
          <button className="insight-trigger" onClick={() => setIsChatOpen((open) => !open)} type="button">
            ✨ AI INSIGHT
          </button>
        </div>
      </header>

      {identityError && <p className="identity-error" role="alert">{identityError}</p>}
      {selectedIdentity && (
        <section className="selected-profile" aria-label="Обраний профіль">
          <p>
            Показано дані: <strong>{selectedIdentity.first_name || selectedIdentity.username || "користувач"}</strong>
            {" · "}Telegram ID {selectedIdentity.telegram_id}
            {selectedIdentity.couples.length > 0 && ` · ${selectedIdentity.couples.length} профіль(і) пари`}
          </p>
          <button onClick={() => {
            setSelectedIdentity(null);
            setTelegramIdInput("");
            setInsightChatThreadId("");
            setInsightChatMessages([]);
            setPendingAction(null);
            setAdminPracticeLibrary(null);
          }} type="button">Показати всі дані</button>
        </section>
      )}

      {error && (
        <section className="error-state" role="alert">
          <p>{error}</p>
          <button onClick={loadDashboard}>Спробувати ще раз</button>
        </section>
      )}

      <section className="summary-grid" aria-label="Підсумок кредитів">
        {cards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span aria-hidden="true">{card.icon}</span>
            <p>{card.label}</p>
            <strong>{formatCredits(card.value)}</strong>
          </article>
        ))}
      </section>

      <section className={`ai-chat-section ${isChatOpen ? "open" : ""}`} aria-labelledby="ai-insight-chat-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">AI INSIGHT · ✨</p>
            <h2 id="ai-insight-chat-heading">Помічник з кредитів Intima</h2>
            <p className="chat-intro">
              Поставте запитання про баланс, списання або категорії. Зміни готуються лише після вашого підтвердження.
            </p>
          </div>
          <div className="chat-header-actions">
            {isChatOpen && <button className="new-chat-button" onClick={startNewInsightChat} type="button">Новий діалог</button>}
            <button className="chat-panel-toggle" onClick={() => setIsChatOpen((open) => !open)} type="button">
              {isChatOpen ? "Згорнути" : "Відкрити чат"}
            </button>
          </div>
        </div>

        <div className="chat-history" aria-live="polite">
          {insightChatMessages.length === 0 ? (
            <div className="chat-welcome">
              <span aria-hidden="true">✨</span>
              <p>Я можу показати баланс, найбільші списання або структуру витрат за місяць.</p>
            </div>
          ) : (
            insightChatMessages.map((message, index) => (
              <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                <span>{message.role === "user" ? "Ви" : "AI INSIGHT"}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}
          {insightChatLoading && (
            <article className="chat-message assistant chat-loading" role="status">
              <span>AI INSIGHT</span>
              <p>Читаю дані кредитів…</p>
            </article>
          )}
        </div>

        {insightChatError && <p className="chat-error" role="alert">{insightChatError}</p>}

        {pendingAction?.status === "pending" && (
          <section className="pending-action-card" aria-labelledby="pending-action-heading">
            <div>
              <p className="eyebrow">ПОТРІБНЕ ПІДТВЕРДЖЕННЯ · 🛡️</p>
              <h3 id="pending-action-heading">Запропонована дія</h3>
            </div>
            <dl className="pending-action-details">
              <div>
                <dt>Тип</dt>
                <dd>{pendingAction.payload.type === "expense" ? "Списання кредитів" : "Нарахування кредитів"}</dd>
              </div>
              <div>
                <dt>Кредити</dt>
                <dd>{formatCredits(pendingAction.payload.amount)}</dd>
              </div>
              <div>
                <dt>Категорія</dt>
                <dd>{pendingAction.payload.category}</dd>
              </div>
              <div>
                <dt>Дата</dt>
                <dd>{formatDate(pendingAction.payload.date)}</dd>
              </div>
              <div className="pending-action-description">
                <dt>Опис</dt>
                <dd>{pendingAction.payload.description || "—"}</dd>
              </div>
            </dl>
            {pendingActionError && <p className="pending-action-error" role="alert">{pendingActionError}</p>}
            <div className="pending-action-buttons">
              <button
                className="confirm-action-button"
                disabled={actionProcessing}
                onClick={handleConfirmPendingAction}
                type="button"
              >
                {actionProcessing ? "Обробляємо…" : "✓ Підтвердити"}
              </button>
              <button
                className="cancel-action-button"
                disabled={actionProcessing}
                onClick={handleCancelPendingAction}
                type="button"
              >
                Скасувати
              </button>
            </div>
          </section>
        )}

        <form className="chat-form" onSubmit={handleInsightChatSubmit}>
          <label className="visually-hidden" htmlFor="ai-insight-chat-input">Запит до AI INSIGHT</label>
          <textarea
            id="ai-insight-chat-input"
            disabled={insightChatLoading}
            onChange={(event) => setInsightChatInput(event.target.value)}
            placeholder="Наприклад: Який мій баланс і найбільші списання?"
            rows="2"
            value={insightChatInput}
          />
          <button className="chat-send-button" disabled={insightChatLoading || !insightChatInput.trim()} type="submit">
            {insightChatLoading ? "Аналізуємо…" : "Запитати"}
          </button>
        </form>
        <div className="chat-suggestions" aria-label="Приклади фінансових запитів">
          <button onClick={() => setInsightChatInput("Який поточний баланс кредитів?")} type="button">💜 Баланс</button>
          <button onClick={() => setInsightChatInput("Покажи найбільші списання")} type="button">🌿 Списання</button>
          <button onClick={() => setInsightChatInput("На що витратили найбільше кредитів?")} type="button">📊 Категорії</button>
          <button onClick={() => setInsightChatInput("Списати 3 кредити за AI-сесію сьогодні")} type="button">🛡️ Підготувати списання</button>
        </div>
      </section>

      <section className="transaction-form-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">НОВА ОПЕРАЦІЯ · ✦</p>
            <h2>Додати кредити Intima</h2>
          </div>
          <button
            aria-expanded={formOpen}
            className="form-toggle"
            onClick={() => setFormOpen((isOpen) => !isOpen)}
            type="button"
          >
            {formOpen ? "Згорнути форму" : "＋ Додати операцію"}
          </button>
        </div>
        {!formOpen && <p className="form-hint">Нараховуйте бонуси або списуйте кредити за AI-сесії, вправи й персональні плани. 🫶</p>}
        {formOpen && <form className="transaction-form" onSubmit={handleSubmit}>
          <label>
            Тип
            <select name="type" value={form.type} onChange={handleChange}>
              <option value="income">Нарахування</option>
              <option value="expense">Списання</option>
            </select>
          </label>
          <label>
            Кредити
            <input name="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={handleChange} required />
          </label>
          <label>
            Категорія
            <input name="category" value={form.category} onChange={handleChange} placeholder="Наприклад, AI-сесія" required />
          </label>
          <label>
            Дата
            <input name="date" type="date" value={form.date} onChange={handleChange} required />
          </label>
          <label className="form-description">
            Опис <span>(необов’язково)</span>
            <textarea name="description" value={form.description} onChange={handleChange} placeholder="Наприклад, Списано 3 кредити за персональний план" rows="3" />
          </label>
          {formError && <p className="form-error" role="alert">{formError}</p>}
          <button className="submit-button" type="submit" disabled={submitting}>
            {submitting ? "Зберігаємо…" : "Додати операцію"}
          </button>
        </form>}
      </section>

      <div className="overview-grid">
      <section className="activity-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">LEDGER</p>
            <h2>Історія кредитів</h2>
          </div>
          <div className="filter-group" aria-label="Фільтр операцій">
            {filters.map((item) => (
              <button
                className={filter === item.value ? "filter-button active" : "filter-button"}
                key={item.value}
                onClick={() => setFilter(item.value)}
                type="button"
              >
                {item.label}
              </button>
            ))}
            <label className="category-filter">
              <span className="visually-hidden">Категорія</span>
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
                <option value="all">Усі категорії</option>
                {categories.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
          </div>
        </div>

        {loading ? (
          <p className="state-message">Завантажуємо дані з API…</p>
        ) : visibleTransactions.length === 0 ? (
          <p className="empty-state">Операцій ще немає. Додайте перше нарахування або списання кредитів.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Кредити</th>
                  <th>Категорія</th>
                  <th>Опис</th>
                  <th><span className="visually-hidden">Дії</span></th>
                </tr>
              </thead>
              <tbody>
                {visibleTransactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td>{formatDate(transaction.date)}</td>
                    <td><span className={`type-badge ${transaction.type}`}>{typeLabels[transaction.type]}</span></td>
                    <td>{formatCredits(transaction.amount)}</td>
                    <td>{transaction.category}</td>
                    <td>{transaction.description || "—"}</td>
                    <td>
                      <button className="delete-button" onClick={() => handleDelete(transaction)} disabled={deletingId === transaction.id} type="button">
                        {deletingId === transaction.id ? "Видаляємо…" : "Видалити"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="expense-structure" aria-label="Структура списань">
          <div className="section-heading">
            <div>
              <p className="eyebrow">СТРУКТУРА СПИСАНЬ</p>
              <h2>Кредити за категоріями</h2>
            </div>
          </div>
          {expenseStructure.length === 0 ? (
            <p className="empty-state">Додайте списання, щоб побачити структуру витрат кредитів.</p>
          ) : (
            <ul className="expense-list">
              {expenseStructure.map((item) => (
                <li key={item.category}>
                  <div className="expense-label">
                    <span>{item.category}</span>
                    <strong>{formatCredits(item.amount)} кредитів · {Math.round(item.share)}%</strong>
                  </div>
                  <div className="expense-bar" aria-label={`${item.category}: ${Math.round(item.share)}%`}>
                    <span style={{ width: `${item.share}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
      </section>
      </div>

      {isPracticesOpen && (
        <div className="practices-overlay" onMouseDown={closePractices} role="presentation">
          <section
            aria-labelledby="practices-heading"
            aria-modal="true"
            className="practices-modal"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <button aria-label="Закрити практики" className="modal-close-button" onClick={closePractices} type="button">×</button>
            {!selectedPractice ? (
              <>
                <p className="eyebrow">{practiceCollection === "self" ? "INTIMA · ДЛЯ СЕБЕ" : "INTIMA · ДЛЯ ВАС ДВОХ"}</p>
                <h2 id="practices-heading">{activePracticeTitle}</h2>
                <p className="practices-intro">
                  {selectedIdentity
                    ? `Баланс профілю: ${formatCredits(adminPracticeLibrary?.balance ?? 0)} кредитів. Відкриття нової практики коштує 1 кредит.`
                    : "Спершу оберіть Telegram ID у верхній частині адмінки, щоб протестувати списання кредиту для профілю."}
                </p>
                <div className="practice-choice-grid">
                  {activeAdminPractices.map((practice) => (
                    <button className="practice-choice" key={practice.id} onClick={() => setSelectedPractice(practice)} type="button">
                      <span aria-hidden="true">{practice.icon}</span>
                      <strong>{practice.label}</strong>
                      <small>
                        {selectedIdentity && adminPracticeLibrary?.practices.find((item) => item.id === practice.id)?.unlocked
                          ? "✓ Уже відкрито"
                          : `1 кредит · ${practice.time}`}
                      </small>
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <button className="back-to-practices" onClick={() => setSelectedPractice(null)} type="button">← Усі практики</button>
                <div className="practice-detail-heading">
                  <span aria-hidden="true">{selectedPractice.icon}</span>
                  <div>
                    <p className="eyebrow">{selectedPractice.time}</p>
                    <h2 id="practices-heading">{selectedPractice.title}</h2>
                  </div>
                </div>
                {selectedAdminPractice?.unlocked ? (
                  <>
                    <p className="practices-intro">{selectedPractice.intro}</p>
                    <ol className="practice-steps">
                      {selectedPractice.steps.map((step) => <li key={step}>{step}</li>)}
                    </ol>
                    <p className="practice-note">💜 {practiceCollection === "self" ? "Обирайте лише те, що комфортно вам. Можна зупинитися, змінити темп або відкласти вправу в будь-який момент." : "Обирайте лише те, що комфортно вам обом. Можна зупинитися, змінити темп або відкласти вправу в будь-який момент."}</p>
                    {practiceCollection === "self" && <p className="practice-warning">⚠️ {selfDiscoveryWarning}</p>}
                  </>
                ) : (
                  <p className="practice-locked-copy">Кроки цієї вправи відкриються для обраного профілю після підтвердження списання 1 кредиту.</p>
                )}
                <div className="admin-practice-access">
                  {!selectedIdentity ? (
                    <p>Оберіть Telegram ID у адмінці, щоб відкрити цю практику для конкретного профілю.</p>
                  ) : selectedAdminPractice?.unlocked ? (
                    <p className="practice-unlocked-status">✓ Ця практика вже відкрита для обраного профілю. Повторного списання не буде.</p>
                  ) : (
                    <>
                      <p>Для профілю буде створено списання 1 кредиту в категорії «Практика Intima».</p>
                      <button
                        className="purchase-confirm-button"
                        disabled={Boolean(adminPracticeOpeningId)}
                        onClick={() => openAdminPractice(selectedPractice)}
                        type="button"
                      >
                        {adminPracticeOpeningId ? "Відкриваємо…" : "Відкрити для профілю за 1 кредит"}
                      </button>
                    </>
                  )}
                  {adminPracticeError && <p className="form-error" role="alert">{adminPracticeError}</p>}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
