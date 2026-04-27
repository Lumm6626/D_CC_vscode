/**
 * Schedule Secretary Dashboard JavaScript
 */

const API_BASE = '/api';

// State
let currentSection = 'dashboard';
let tasks = [];
let schedules = [];
let routines = [];
let currentScheduleDate = new Date().toISOString().split('T')[0];
let aiSuggestions = [];

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initModals();
    initForms();
    initEventListeners();
    loadDashboard();
});

// ==================== Navigation ====================

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;

            // Update nav active state
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // Show section
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');

            currentSection = section;
            loadSection(section);
        });
    });

    // Handle hash navigation
    if (window.location.hash) {
        const section = window.location.hash.slice(1);
        const navItem = document.querySelector(`.nav-item[data-section="${section}"]`);
        if (navItem) navItem.click();
    }
}

function loadSection(section) {
    switch (section) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'tasks':
            loadTasks();
            break;
        case 'schedule':
            loadSchedule();
            break;
        case 'routines':
            loadRoutines();
            break;
        case 'email':
            loadEmailTasks();
            break;
    }
}

// ==================== Dashboard ====================

function loadDashboard() {
    Promise.all([
        apiGet('/dashboard/summary'),
        apiGet('/schedules'),
        apiGet('/routines/summary'),
        apiGet('/tasks')
    ]).then(([summaryRes, schedulesRes, routinesRes, tasksRes]) => {
        if (summaryRes.status === 'ok') {
            const s = summaryRes.summary;
            document.getElementById('stat-total-tasks').textContent = s.total_tasks || 0;
            document.getElementById('stat-pending-tasks').textContent = s.pending_tasks || 0;
            document.getElementById('stat-inprogress-tasks').textContent = s.in_progress_tasks || 0;
            document.getElementById('stat-completed-tasks').textContent = s.completed_tasks || 0;
            document.getElementById('stat-today-schedule').textContent = `${s.today_completed_count || 0}/${s.today_schedule_count || 0}`;
        }

        if (routinesRes.status === 'ok') {
            document.getElementById('stat-today-routines').textContent = routinesRes.summary.today_routines_count || 0;
        }

        if (schedulesRes.status === 'ok') {
            schedules = schedulesRes.schedules;
            renderTodaySchedules(schedules);
        }

        if (tasksRes.status === 'ok') {
            const pendingTasks = tasksRes.tasks.filter(t => t.status !== 'completed');
            const highPriorityTasks = pendingTasks.filter(t => t.priority === 'high').slice(0, 5);
            renderHighPriorityTasks(highPriorityTasks);
        }
    }).catch(console.error);
}

function renderTodaySchedules(schedules) {
    const container = document.getElementById('today-schedule-list');

    const today = new Date().toISOString().split('T')[0];
    const todaySchedules = schedules.filter(s => s.date === today);

    if (todaySchedules.length === 0) {
        container.innerHTML = '<div class="empty-state">今日暂无日程</div>';
        return;
    }

    container.innerHTML = todaySchedules.map(s => {
        const status = s.status === 'done' ? '✅' : s.status === 'missed' ? '❌' : '📅';
        const time = s.start_time ? s.start_time.slice(0, 5) : '';
        const title = s.task_title || s.slot_type || '日程';
        return `
            <div class="schedule-item" data-id="${s.id}">
                <span class="schedule-status ${s.status}">${status}</span>
                <span class="schedule-time">${time}</span>
                <span class="task-title">${title}</span>
            </div>
        `;
    }).join('');
}

function renderHighPriorityTasks(tasks) {
    const container = document.getElementById('high-priority-list');

    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无紧急任务</div>';
        return;
    }

    container.innerHTML = tasks.map(t => `
        <div class="task-item" data-id="${t.id}">
            <span class="task-priority ${t.priority}"></span>
            <div class="task-content">
                <div class="task-title">${escapeHtml(t.title)}</div>
                <div class="task-meta">${t.source || 'manual'}</div>
            </div>
            <div class="task-actions">
                <button class="btn-icon" onclick="completeTask(${t.id})">✓</button>
            </div>
        </div>
    `).join('');
}

// ==================== Tasks ====================

function loadTasks() {
    const status = document.getElementById('task-filter-status').value;
    const source = document.getElementById('task-filter-source').value;
    const priority = document.getElementById('task-filter-priority').value;

    let url = '/tasks?';
    if (status) url += `status=${status}&`;
    if (source) url += `source=${source}&`;
    if (priority) url += `priority=${priority}&`;

    apiGet(url).then(res => {
        if (res.status === 'ok') {
            tasks = res.tasks;
            renderTasks(tasks);
        }
    }).catch(console.error);
}

function renderTasks(tasks) {
    const container = document.getElementById('task-list');

    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无任务</div>';
        return;
    }

    container.innerHTML = tasks.map(t => {
        const priorityLabel = t.priority === 'high' ? '紧急' : t.priority === 'normal' ? '普通' : '低';
        const statusLabel = t.status === 'pending' ? '待处理' : t.status === 'in_progress' ? '进行中' : '已完成';
        const dueDate = t.due_date ? ` | 截止: ${t.due_date}` : '';

        return `
            <div class="task-item" data-id="${t.id}">
                <span class="task-priority ${t.priority}"></span>
                <div class="task-content">
                    <div class="task-title">${escapeHtml(t.title)}</div>
                    <div class="task-meta">${t.source || 'manual'} | ${statusLabel} | ${priorityLabel}${dueDate}</div>
                </div>
                <div class="task-actions">
                    <button class="btn-icon" onclick="editTask(${t.id})" title="编辑">✏️</button>
                    <button class="btn-icon" onclick="scheduleTask(${t.id})" title="安排">🗓️</button>
                    ${t.status !== 'completed' ? `<button class="btn-icon" onclick="completeTask(${t.id})" title="完成">✓</button>` : ''}
                    <button class="btn-icon" onclick="deleteTask(${t.id})" title="删除">🗑️</button>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== Schedule ====================

function loadSchedule() {
    const dateInput = document.getElementById('schedule-date');
    if (!dateInput.value) {
        dateInput.value = currentScheduleDate;
    }

    loadScheduleForDate(dateInput.value);
    loadAvailableSlots(dateInput.value);
}

function loadScheduleForDate(date) {
    apiGet(`/schedules?date=${date}`).then(res => {
        if (res.status === 'ok') {
            schedules = res.schedules;
            renderTimeline(date, schedules);
        }
    }).catch(console.error);
}

function loadAvailableSlots(date) {
    apiGet(`/schedules/available-slots?date=${date}`).then(res => {
        if (res.status === 'ok') {
            renderAvailableSlots(res.slots);
        }
    }).catch(console.error);
}

function renderTimeline(date, schedules) {
    const container = document.getElementById('schedule-timeline');

    // Filter schedules for the date
    const daySchedules = schedules.filter(s => s.date === date);

    let html = '';
    for (let hour = 8; hour <= 20; hour++) {
        const hourStr = hour.toString().padStart(2, '0');
        const slotSchedules = daySchedules.filter(s => {
            if (!s.start_time) return false;
            const startHour = parseInt(s.start_time.split(':')[0]);
            return startHour === hour;
        });

        html += `
            <div class="time-slot">
                <div class="time-slot-label">${hourStr}:00</div>
                <div class="slot-content">
                    ${slotSchedules.map(s => `
                        <div class="slot-item ${s.slot_type} ${s.status || ''}"
                             data-id="${s.id}"
                             onclick="openScheduleModal(${s.id})">
                            ${s.task_title || s.slot_type}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderAvailableSlots(slots) {
    const container = document.getElementById('available-slots-list');

    if (slots.length === 0) {
        container.innerHTML = '<div class="empty-state">今日已满</div>';
        return;
    }

    container.innerHTML = slots.map(s => `
        <div class="routine-item">
            <span class="routine-time">${s.hour}:00 - ${s.hour + 1}:00</span>
            <button class="btn-secondary" onclick="openScheduleModalForSlot('${s.start_time}', '${s.end_time}')">
                添加到此时间段
            </button>
        </div>
    `).join('');
}

// ==================== Routines ====================

function loadRoutines() {
    apiGet('/routines').then(res => {
        if (res.status === 'ok') {
            routines = res.routines;
            renderRoutines(routines);
        }
    }).catch(console.error);
}

function renderRoutines(routines) {
    const container = document.getElementById('routine-list');

    if (routines.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无日常任务</div>';
        return;
    }

    const dayNames = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'];

    container.innerHTML = routines.map(r => {
        const time = r.time_of_day ? r.time_of_day.slice(0, 5) : '';
        const days = (r.days_of_week || []).map(d => dayNames[d]).join(', ');
        const activeClass = r.is_active ? '' : 'inactive';

        return `
            <div class="routine-item" data-id="${r.id}">
                <span class="routine-time">${time}</span>
                <div class="task-content">
                    <div class="task-title">${escapeHtml(r.title)}</div>
                    <div class="task-meta">${days} | ${r.duration_minutes}分钟</div>
                </div>
                <span class="routine-active ${activeClass}">${r.is_active ? '启用' : '停用'}</span>
                <div class="task-actions">
                    <button class="btn-icon" onclick="triggerRoutine(${r.id})" title="触发">▶️</button>
                    <button class="btn-icon" onclick="editRoutine(${r.id})" title="编辑">✏️</button>
                    <button class="btn-icon" onclick="deleteRoutine(${r.id})" title="删除">🗑️</button>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== Email ====================

function loadEmailTasks() {
    // Just show placeholder, will load on button click
    document.getElementById('email-task-list').innerHTML =
        '<div class="empty-state">点击「导入到任务池」按钮从邮件提取待办</div>';
}

function importEmailTasks() {
    apiPost('/import-from-email', {}).then(res => {
        if (res.status === 'ok') {
            showNotification(`成功导入 ${res.imported_count} 个任务`);
            if (res.tasks && res.tasks.length > 0) {
                renderEmailTasks(res.tasks);
            }
            // Refresh dashboard
            loadDashboard();
        } else {
            showNotification('导入失败: ' + res.error, 'error');
        }
    }).catch(err => {
        showNotification('导入失败', 'error');
        console.error(err);
    });
}

function renderEmailTasks(tasks) {
    const container = document.getElementById('email-task-list');

    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">未从邮件中找到待办事项</div>';
        return;
    }

    container.innerHTML = tasks.map(t => `
        <div class="task-item">
            <span class="task-priority ${t.priority}"></span>
            <div class="task-content">
                <div class="task-title">${escapeHtml(t.title)}</div>
                <div class="task-meta">来自: ${escapeHtml(t.from_email || '未知')}</div>
            </div>
        </div>
    `).join('');
}

// ==================== Task Actions ====================

function completeTask(taskId) {
    apiPost(`/tasks/${taskId}/complete`, {}).then(res => {
        if (res.status === 'ok') {
            showNotification('任务已完成');
            loadSection(currentSection);
            loadDashboard();
        }
    }).catch(console.error);
}

function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？')) return;

    apiDelete(`/tasks/${taskId}`).then(res => {
        if (res.status === 'ok') {
            showNotification('任务已删除');
            loadSection(currentSection);
            loadDashboard();
        }
    }).catch(console.error);
}

function scheduleTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('schedule-task-id').value = taskId;
    document.getElementById('schedule-date-input').value = currentScheduleDate;
    document.getElementById('schedule-slot-type').value = 'task';
    document.getElementById('schedule-id').value = '';

    openModal('schedule-modal');
}

// ==================== AI Suggestions ====================

function showAiSuggestions() {
    const date = document.getElementById('schedule-date').value;

    openModal('ai-suggest-modal');
    document.getElementById('ai-suggest-content').innerHTML = '<div class="loading">正在生成建议...</div>';

    apiPost('/schedule/ai-suggest', { date }).then(res => {
        if (res.status === 'ok') {
            aiSuggestions = res.suggestion.suggestions || [];
            renderAiSuggestions(aiSuggestions);
        } else {
            document.getElementById('ai-suggest-content').innerHTML =
                '<div class="empty-state">生成建议失败</div>';
        }
    }).catch(err => {
        document.getElementById('ai-suggest-content').innerHTML =
            '<div class="empty-state">生成建议失败</div>';
        console.error(err);
    });
}

function renderAiSuggestions(suggestions) {
    const container = document.getElementById('ai-suggest-content');

    if (suggestions.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无建议</div>';
        return;
    }

    container.innerHTML = suggestions.map((s, i) => `
        <div class="ai-suggest-item">
            <input type="checkbox" checked data-index="${i}">
            <span class="ai-suggest-time">${s.start_time?.slice(0,5)} - ${s.end_time?.slice(0,5)}</span>
            <span>${escapeHtml(s.task_title)}</span>
        </div>
    `).join('');
}

function applyAiSuggestions() {
    const date = document.getElementById('schedule-date').value;
    const checkboxes = document.querySelectorAll('#ai-suggest-content input[type="checkbox"]:checked');

    const toApply = [];
    checkboxes.forEach(cb => {
        const idx = parseInt(cb.dataset.index);
        const suggestion = aiSuggestions[idx];
        if (suggestion) {
            toApply.push({
                task_id: suggestion.task_id,
                date: date,
                start_time: suggestion.start_time,
                end_time: suggestion.end_time
            });
        }
    });

    if (toApply.length === 0) {
        showNotification('请选择要应用的任务');
        return;
    }

    apiPost('/schedule/apply-suggestion', { suggestions: toApply }).then(res => {
        if (res.status === 'ok') {
            showNotification(`已安排 ${res.applied_count} 个任务`);
            closeModal('ai-suggest-modal');
            loadSchedule();
            loadDashboard();
        }
    }).catch(console.error);
}

// ==================== Modal Handling ====================

function initModals() {
    // Task modal
    document.getElementById('add-task-btn').addEventListener('click', () => {
        document.getElementById('task-modal-title').textContent = '添加任务';
        document.getElementById('task-form').reset();
        document.getElementById('task-id').value = '';
        openModal('task-modal');
    });

    document.getElementById('task-cancel-btn').addEventListener('click', () => {
        closeModal('task-modal');
    });

    // Schedule modal
    document.getElementById('schedule-cancel-btn').addEventListener('click', () => {
        closeModal('schedule-modal');
    });

    // Routine modal
    document.getElementById('add-routine-btn').addEventListener('click', () => {
        document.getElementById('routine-modal-title').textContent = '添加日常任务';
        document.getElementById('routine-form').reset();
        document.getElementById('routine-id').value = '';
        openModal('routine-modal');
    });

    document.getElementById('routine-cancel-btn').addEventListener('click', () => {
        closeModal('routine-modal');
    });

    // AI suggest modal
    document.getElementById('ai-suggest-btn').addEventListener('click', showAiSuggestions);
    document.getElementById('ai-suggest-close-btn').addEventListener('click', () => {
        closeModal('ai-suggest-modal');
    });
    document.getElementById('ai-suggest-apply-btn').addEventListener('click', applyAiSuggestions);

    // Import email
    document.getElementById('import-email-btn').addEventListener('click', importEmailTasks);

    // Schedule date change
    document.getElementById('schedule-date').addEventListener('change', (e) => {
        currentScheduleDate = e.target.value;
        loadScheduleForDate(currentScheduleDate);
        loadAvailableSlots(currentScheduleDate);
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadSection(currentSection);
    });

    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function openScheduleModal(scheduleId) {
    const schedule = schedules.find(s => s.id === scheduleId);
    if (!schedule) return;

    document.getElementById('schedule-id').value = schedule.id;
    document.getElementById('schedule-task-id').value = schedule.task_id || '';
    document.getElementById('schedule-date-input').value = schedule.date || currentScheduleDate;
    document.getElementById('schedule-start-time').value = schedule.start_time ? schedule.start_time.slice(0,5) : '';
    document.getElementById('schedule-end-time').value = schedule.end_time ? schedule.end_time.slice(0,5) : '';
    document.getElementById('schedule-slot-type').value = schedule.slot_type || 'task';

    openModal('schedule-modal');
}

function openScheduleModalForSlot(startTime, endTime) {
    document.getElementById('schedule-id').value = '';
    document.getElementById('schedule-task-id').value = '';
    document.getElementById('schedule-date-input').value = currentScheduleDate;
    document.getElementById('schedule-start-time').value = startTime.slice(0,5);
    document.getElementById('schedule-end-time').value = endTime.slice(0,5);
    document.getElementById('schedule-slot-type').value = 'task';

    openModal('schedule-modal');
}

// ==================== Forms ====================

function initForms() {
    // Task form
    document.getElementById('task-form').addEventListener('submit', (e) => {
        e.preventDefault();
        submitTaskForm();
    });

    // Schedule form
    document.getElementById('schedule-form').addEventListener('submit', (e) => {
        e.preventDefault();
        submitScheduleForm();
    });

    // Routine form
    document.getElementById('routine-form').addEventListener('submit', (e) => {
        e.preventDefault();
        submitRoutineForm();
    });

    // Task filters
    ['task-filter-status', 'task-filter-source', 'task-filter-priority'].forEach(id => {
        document.getElementById(id).addEventListener('change', loadTasks);
    });
}

function submitTaskForm() {
    const taskId = document.getElementById('task-id').value;
    const data = {
        title: document.getElementById('task-title').value,
        description: document.getElementById('task-description').value,
        priority: document.getElementById('task-priority').value,
        due_date: document.getElementById('task-due-date').value || null,
        estimated_hours: parseFloat(document.getElementById('task-estimated-hours').value) || null
    };

    const method = taskId ? 'PUT' : 'POST';
    const url = taskId ? `/tasks/${taskId}` : '/tasks';

    api(url, method, data).then(res => {
        if (res.status === 'ok') {
            showNotification(taskId ? '任务已更新' : '任务已添加');
            closeModal('task-modal');
            loadTasks();
            loadDashboard();
        }
    }).catch(console.error);
}

function submitScheduleForm() {
    const scheduleId = document.getElementById('schedule-id').value;
    const data = {
        date: document.getElementById('schedule-date-input').value,
        start_time: document.getElementById('schedule-start-time').value,
        end_time: document.getElementById('schedule-end-time').value,
        slot_type: document.getElementById('schedule-slot-type').value,
        task_id: document.getElementById('schedule-task-id').value || null
    };

    const method = scheduleId ? 'PUT' : 'POST';
    const url = scheduleId ? `/schedules/${scheduleId}` : '/schedules';

    api(url, method, data).then(res => {
        if (res.status === 'ok') {
            showNotification(scheduleId ? '日程已更新' : '日程已添加');
            closeModal('schedule-modal');
            loadSchedule();
            loadDashboard();
        }
    }).catch(console.error);
}

function submitRoutineForm() {
    const routineId = document.getElementById('routine-id').value;
    const days = Array.from(document.querySelectorAll('input[name="routine-days"]:checked'))
        .map(cb => parseInt(cb.value));

    const data = {
        title: document.getElementById('routine-title').value,
        description: document.getElementById('routine-description').value,
        time_of_day: document.getElementById('routine-time').value,
        duration_minutes: parseInt(document.getElementById('routine-duration').value),
        days_of_week: days
    };

    const method = routineId ? 'PUT' : 'POST';
    const url = routineId ? `/routines/${routineId}` : '/routines';

    api(url, method, data).then(res => {
        if (res.status === 'ok') {
            showNotification(routineId ? '日常任务已更新' : '日常任务已添加');
            closeModal('routine-modal');
            loadRoutines();
        }
    }).catch(console.error);
}

function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('task-modal-title').textContent = '编辑任务';
    document.getElementById('task-id').value = task.id;
    document.getElementById('task-title').value = task.title;
    document.getElementById('task-description').value = task.description || '';
    document.getElementById('task-priority').value = task.priority || 'normal';
    document.getElementById('task-due-date').value = task.due_date || '';
    document.getElementById('task-estimated-hours').value = task.estimated_hours || '';

    openModal('task-modal');
}

function editRoutine(routineId) {
    const routine = routines.find(r => r.id === routineId);
    if (!routine) return;

    document.getElementById('routine-modal-title').textContent = '编辑日常任务';
    document.getElementById('routine-id').value = routine.id;
    document.getElementById('routine-title').value = routine.title;
    document.getElementById('routine-description').value = routine.description || '';
    document.getElementById('routine-time').value = routine.time_of_day ? routine.time_of_day.slice(0,5) : '';
    document.getElementById('routine-duration').value = routine.duration_minutes || 60;

    // Set days
    document.querySelectorAll('input[name="routine-days"]').forEach(cb => {
        cb.checked = (routine.days_of_week || []).includes(parseInt(cb.value));
    });

    openModal('routine-modal');
}

function deleteRoutine(routineId) {
    if (!confirm('确定要删除这个日常任务吗？')) return;

    apiDelete(`/routines/${routineId}`).then(res => {
        if (res.status === 'ok') {
            showNotification('日常任务已删除');
            loadRoutines();
        }
    }).catch(console.error);
}

function triggerRoutine(routineId) {
    apiPost(`/routines/${routineId}/trigger`, {}).then(res => {
        if (res.success) {
            showNotification(res.message);
            loadDashboard();
        } else {
            showNotification('触发失败: ' + res.message, 'error');
        }
    }).catch(console.error);
}

// ==================== Event Listeners ====================

function initEventListeners() {
    // Task filters
    document.getElementById('task-filter-status').addEventListener('change', loadTasks);
    document.getElementById('task-filter-source').addEventListener('change', loadTasks);
    document.getElementById('task-filter-priority').addEventListener('change', loadTasks);
}

// ==================== API Helpers ====================

async function api(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const res = await fetch(API_BASE + url, options);
    return res.json();
}

async function apiGet(url) {
    return api(url);
}

async function apiPost(url, data) {
    return api(url, 'POST', data);
}

async function apiDelete(url) {
    return api(url, 'DELETE');
}

// ==================== Utilities ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'success') {
    // Simple alert for now, could be replaced with toast
    alert(message);
}
