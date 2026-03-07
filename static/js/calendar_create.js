/**
 * calendar_create.js — FullCalendar mode création de créneaux
 *
 * Globals expected from template:
 *   EXISTING_SLOTS — Array of {id?, start, end} (undefined on create page)
 */

(function () {
  'use strict';

  // Internal slot list [{id, start, end, calId}]
  let slots = [];
  let nextCalId = 1;

  // Load existing slots if any (edit mode)
  if (typeof EXISTING_SLOTS !== 'undefined' && Array.isArray(EXISTING_SLOTS)) {
    EXISTING_SLOTS.forEach(function (s) {
      slots.push({ id: s.id || null, start: s.start, end: s.end, calId: String(nextCalId++) });
    });
  }

  function slotsToEvents() {
    return slots.map(function (s) {
      return {
        id: s.calId,
        start: s.start,
        end: s.end,
        backgroundColor: '#6b7280',
        borderColor: '#4b5563',
        textColor: '#ffffff',
        extendedProps: { serverSlotId: s.id },
      };
    });
  }

  function serializeSlots() {
    return slots.map(function (s) {
      const obj = { start: s.start, end: s.end };
      if (s.id) obj.id = s.id;
      return obj;
    });
  }

  function updateHiddenField() {
    const field = document.getElementById('id_time_slots_json');
    if (field) {
      field.value = JSON.stringify(serializeSlots());
    }
  }

  function deleteSlot(calId) {
    slots = slots.filter(function (s) { return s.calId !== calId; });
    updateHiddenField();
  }

  function renderEventContent(info) {
    const calId = info.event.id;
    const container = document.createElement('div');
    container.className = 'fc-create-event';

    const timeEl = document.createElement('span');
    timeEl.className = 'fc-event-time-custom';
    timeEl.textContent = info.timeText;
    container.appendChild(timeEl);

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'fc-delete-btn';
    delBtn.textContent = '×';
    delBtn.title = 'Supprimer ce créneau';
    delBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (confirm('Supprimer ce créneau ?')) {
        calendar.getEventById(calId).remove();
        deleteSlot(calId);
      }
    });
    container.appendChild(delBtn);

    return { domNodes: [container] };
  }

  const calendarEl = document.getElementById('calendar');
  const isMobile = window.innerWidth < 768;

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: isMobile ? 'timeGridDay' : 'timeGridWeek',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: isMobile ? 'timeGridDay,listWeek' : 'timeGridWeek,dayGridMonth',
    },
    locale: 'fr',
    firstDay: 1,
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    allDaySlot: false,
    selectable: true,
    editable: true,
    eventResizableFromStart: true,
    events: slotsToEvents(),
    eventContent: renderEventContent,

    select: function (info) {
      const calId = String(nextCalId++);
      slots.push({
        id: null,
        start: info.startStr,
        end: info.endStr,
        calId: calId,
      });
      calendar.addEvent({
        id: calId,
        start: info.start,
        end: info.end,
        backgroundColor: '#6b7280',
        borderColor: '#4b5563',
        textColor: '#ffffff',
        extendedProps: { serverSlotId: null },
      });
      calendar.unselect();
      updateHiddenField();
    },

    eventDrop: function (info) {
      const calId = info.event.id;
      const slot = slots.find(function (s) { return s.calId === calId; });
      if (slot) {
        slot.start = info.event.startStr;
        slot.end = info.event.endStr;
        updateHiddenField();
      }
    },

    eventResize: function (info) {
      const calId = info.event.id;
      const slot = slots.find(function (s) { return s.calId === calId; });
      if (slot) {
        slot.start = info.event.startStr;
        slot.end = info.event.endStr;
        updateHiddenField();
      }
    },
  });

  calendar.render();
  updateHiddenField();

  // Serialize before form submit
  const form = document.getElementById('poll-create-form') || document.getElementById('poll-edit-form');
  if (form) {
    form.addEventListener('submit', function () {
      updateHiddenField();
    });
  }

  // Responsive resize
  window.addEventListener('resize', function () {
    if (window.innerWidth < 768 && calendar.view.type === 'timeGridWeek') {
      calendar.changeView('timeGridDay');
    }
  });
})();
