const $ = (id) => document.getElementById(id);

const els = {
  profileSelect: $('profileSelect'),
  saveProfileBtn: $('saveProfileBtn'),
  deleteProfileBtn: $('deleteProfileBtn'),
  firstName: $('firstName'),
  lastName: $('lastName'),
  sexMale: $('sexMale'),
  sexFemale: $('sexFemale'),
  goalWeight: $('goalWeight'),
  goalFat: $('goalFat'),
  weightRow: $('weightRow'),
  fatBlock: $('fatBlock'),
  targetWeight: $('targetWeight'),
  currentFat: $('currentFat'),
  targetFat: $('targetFat'),
  autoSaveCsv: $('autoSaveCsv'),
  calculateBtn: $('calculateBtn'),
  clearBtn: $('clearBtn'),
  weight: $('weight'),
  height: $('height'),
  age: $('age'),
  steps: $('steps'),
  workouts: $('workouts'),
  minutesPerWorkout: $('minutesPerWorkout'),
  proteinWeek: $('proteinWeek'),
  fatWeek: $('fatWeek'),
  carbsWeek: $('carbsWeek'),
  caloriesDay: $('caloriesDay'),
  result: $('result'),
  resultGoal: $('resultGoal'),
  resultBmr: $('resultBmr'),
  resultTdee: $('resultTdee'),
  statusCard: $('statusCard'),
  statusEmoji: $('statusEmoji'),
  statusTitle: $('statusTitle'),
  statusText: $('statusText'),
  foodText: $('foodText'),
  timeText: $('timeText')
};

const INT_INPUTS = [...document.querySelectorAll('input[data-int="true"]')];

function cleanIntValue(value, { allowEmpty = true } = {}) {
  if (value === '' || value === null || value === undefined) return allowEmpty ? '' : 0;
  const digits = String(value).replace(/[^\d]/g, '');
  if (!digits) return allowEmpty ? '' : 0;
  const parsed = Number.parseInt(digits, 10);
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return parsed;
}

function enforceIntegerInput(input) {
  const cleaned = cleanIntValue(input.value);
  input.value = cleaned === '' ? '' : String(cleaned);
}

function numberValue(input, { max = null } = {}) {
  let cleaned = cleanIntValue(input.value, { allowEmpty: false });
  if (typeof max === 'number') cleaned = Math.min(max, cleaned);
  input.value = String(cleaned);
  return cleaned;
}

function currentSex() {
  return els.sexFemale.checked ? 'female' : 'male';
}

function currentGoalType() {
  return els.goalFat.checked ? 'fat' : 'weight';
}

function toggleGoalRows() {
  const byFat = currentGoalType() === 'fat';
  els.weightRow.hidden = byFat;
  els.fatBlock.hidden = !byFat;
}

function normalizeSexForUi(value) {
  const raw = String(value || '').trim().toLowerCase();
  return raw === 'female' || raw === 'женщина' ? 'female' : 'male';
}

function normalizeGoalTypeForUi(value) {
  const raw = String(value || '').trim().toLowerCase();
  return raw === 'fat' || raw === 'жир' ? 'fat' : 'weight';
}

function getPayload() {
  const goalType = currentGoalType();

  return {
    firstName: els.firstName.value.trim(),
    lastName: els.lastName.value.trim(),
    sex: currentSex(),
    goalType,
    targetWeight: goalType === 'weight' ? numberValue(els.targetWeight) : null,
    currentFat: goalType === 'fat' ? numberValue(els.currentFat, { max: 100 }) : null,
    targetFat: goalType === 'fat' ? numberValue(els.targetFat, { max: 100 }) : null,
    autoSaveCsv: els.autoSaveCsv.checked,
    weight: numberValue(els.weight),
    height: numberValue(els.height),
    age: numberValue(els.age),
    steps: numberValue(els.steps),
    workouts: numberValue(els.workouts),
    minutesPerWorkout: numberValue(els.minutesPerWorkout),
    proteinWeek: numberValue(els.proteinWeek),
    fatWeek: numberValue(els.fatWeek),
    carbsWeek: numberValue(els.carbsWeek),
    caloriesDay: numberValue(els.caloriesDay)
  };
}

function setFormData(data = {}) {
  els.firstName.value = data.first_name ?? data.firstName ?? '';
  els.lastName.value = data.last_name ?? data.lastName ?? '';

  if (normalizeSexForUi(data.sex) === 'female') {
    els.sexFemale.checked = true;
  } else {
    els.sexMale.checked = true;
  }

  if (normalizeGoalTypeForUi(data.goal_mode ?? data.goalType) === 'fat') {
    els.goalFat.checked = true;
  } else {
    els.goalWeight.checked = true;
  }

  toggleGoalRows();

  const mappings = [
    ['targetWeight', data.goal_weight ?? data.targetWeight],
    ['currentFat', data.current_body_fat ?? data.currentFat],
    ['targetFat', data.target_body_fat ?? data.targetFat],
    ['weight', data.current_weight ?? data.weight],
    ['height', data.current_height ?? data.height],
    ['age', data.current_age ?? data.age],
    ['steps', data.steps_per_day ?? data.steps],
    ['workouts', data.trainings_per_week ?? data.workouts],
    ['minutesPerWorkout', data.training_minutes ?? data.minutesPerWorkout],
    ['proteinWeek', data.weekly_protein ?? data.proteinWeek],
    ['fatWeek', data.weekly_fat ?? data.fatWeek],
    ['carbsWeek', data.weekly_carbs ?? data.carbsWeek],
    ['caloriesDay', data.avg_kcal_per_day ?? data.caloriesDay]
  ];

  mappings.forEach(([key, value]) => {
    els[key].value = value || value === 0 ? String(cleanIntValue(value, { allowEmpty: false })) : '';
  });

  els.autoSaveCsv.checked = Boolean(data.autoSaveCsv ?? true);
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json().catch(() => ({ ok: false, error: 'Сервер вернул непонятный ответ.' }));
  if (!response.ok || !data.ok) {
    throw new Error(data.error || 'Не удалось выполнить запрос.');
  }
  return data;
}

async function refreshProfileSelect(selectedName = '') {
  const response = await apiRequest('/api/profiles', { method: 'GET' });
  const profiles = Array.isArray(response.profiles) ? response.profiles : [];

  els.profileSelect.innerHTML = '<option value="">Новый профиль</option>';
  profiles.forEach((profileName) => {
    const option = document.createElement('option');
    option.value = profileName;
    option.textContent = profileName;
    option.title = profileName;
    els.profileSelect.appendChild(option);
  });

  els.profileSelect.value = selectedName || '';
  els.profileSelect.title = els.profileSelect.selectedOptions[0]?.textContent || 'Выбор профиля';
}

async function saveCurrentProfile() {
  const payload = getPayload();
  const fullName = [payload.firstName, payload.lastName].filter(Boolean).join(' ').trim();

  if (!fullName) {
    alert('Чтобы сохранить профиль, укажи имя и фамилию.');
    return;
  }

  const response = await apiRequest('/api/profiles', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  await refreshProfileSelect(response.profile_name);
}

async function loadSelectedProfile() {
  const profileName = els.profileSelect.value;
  if (!profileName) return;

  const response = await apiRequest(`/api/profiles/${encodeURIComponent(profileName)}`, {
    method: 'GET'
  });

  setFormData(response.profile);
  els.profileSelect.title = profileName;
}

async function deleteSelectedProfile() {
  const profileName = els.profileSelect.value;
  if (!profileName) {
    alert('Сейчас удалять нечего.');
    return;
  }

  await apiRequest(`/api/profiles/${encodeURIComponent(profileName)}`, {
    method: 'DELETE'
  });

  await refreshProfileSelect('');
}

function statusClassFromKey(key) {
  if (key === 'green') return 'good';
  if (key === 'yellow' || key === 'orange') return 'mid';
  return 'bad';
}

function renderResult(result) {
  const status = result.status || {};
  const meta = result.meta || {};

  els.resultGoal.textContent = result.goal_text || '-';
  els.resultBmr.textContent = `${result.bmr ?? 0} ккал`;
  els.resultTdee.textContent = `${result.tdee ?? 0} ккал`;
  els.statusCard.className = `status-card ${statusClassFromKey(status.key)}`;
  els.statusEmoji.textContent = status.emoji || '🙂';
  els.statusTitle.textContent = status.title || 'Статус';
  els.statusText.textContent = status.subtitle || '-';
  els.foodText.textContent = `В среднем в день: белки ${meta.protein_per_day ?? 0} г, жиры ${meta.fat_per_day ?? 0} г, углеводы ${meta.carbs_per_day ?? 0} г, питание ${getPayload().caloriesDay} ккал.`;
  els.timeText.textContent = result.timeline || '-';
  els.result.classList.add('active');
}

async function calculate() {
  const payload = getPayload();
  const response = await apiRequest('/api/calculate', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  renderResult(response.result);
}

function clearResult() {
  els.result.classList.remove('active');
  els.resultGoal.textContent = '-';
  els.resultBmr.textContent = '-';
  els.resultTdee.textContent = '-';
  els.statusEmoji.textContent = '🙂';
  els.statusTitle.textContent = 'Статус';
  els.statusText.textContent = '-';
  els.foodText.textContent = '-';
  els.timeText.textContent = '-';
}

function bindIntegerInputs() {
  INT_INPUTS.forEach((input) => {
    input.addEventListener('input', () => enforceIntegerInput(input));
    input.addEventListener('blur', () => {
      const cleaned = cleanIntValue(input.value, { allowEmpty: false });
      input.value = String(cleaned);
    });
    input.addEventListener('keydown', (event) => {
      if (['e', 'E', '+', '-', '.', ','].includes(event.key)) {
        event.preventDefault();
      }
    });
  });
}

function bindEvents() {
  els.goalWeight.addEventListener('change', toggleGoalRows);
  els.goalFat.addEventListener('change', toggleGoalRows);

  els.profileSelect.addEventListener('change', () => {
    loadSelectedProfile().catch((error) => alert(error.message));
  });

  els.saveProfileBtn.addEventListener('click', () => {
    saveCurrentProfile().catch((error) => alert(error.message));
  });

  els.deleteProfileBtn.addEventListener('click', () => {
    deleteSelectedProfile().catch((error) => alert(error.message));
  });

  els.calculateBtn.addEventListener('click', () => {
    calculate().catch((error) => alert(error.message));
  });

  els.clearBtn.addEventListener('click', clearResult);
}

async function init() {
  bindIntegerInputs();
  bindEvents();
  toggleGoalRows();
  await refreshProfileSelect('');
}

document.addEventListener('DOMContentLoaded', () => {
  init().catch((error) => {
    alert(error.message || 'Не удалось инициализировать приложение.');
  });
});
  </script>
</body>
</html> напиши полностью что удалять и что вставлять в этмо коде
