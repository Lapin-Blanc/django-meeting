/**
 * calendar_vote.js — FullCalendar mode vote participant
 *
 * Globals expected from template:
 *   POLL_SLOTS       — Array of {id, start, end, choice}
 *   VOTE_SUBMIT_URL  — URL to POST votes (undefined if IS_CLOSED)
 *   CSRF_TOKEN       — Django CSRF token (undefined if IS_CLOSED)
 *   IS_CLOSED        — Boolean (true if read-only mode)
 *   CHOSEN_SLOT_ID   — String UUID of chosen slot (if any)
 */

(function () {
  'use strict';

  const isClosed = typeof IS_CLOSED !== 'undefined' && IS_CLOSED;
  const chosenSlotId = typeof CHOSEN_SLOT_ID !== 'undefined' ? CHOSEN_SLOT_ID : '';

  // Vote state: {slotId: 'yes'|'maybe'|'no'|''}
  const voteState = {};
  POLL_SLOTS.forEach(function (s) {
    voteState[s.id] = s.choice || '';
  });

  function choiceColor(choice, isChosen) {
    if (isChosen) return '#7c3aed'; // purple for chosen slot
    if (choice === 'yes') return '#16a34a';
    if (choice === 'maybe') return '#d97706';
    if (choice === 'no') return '#dc2626';
    return '#6b7280'; // grey = not voted
  }

  function buildEvents() {
    return POLL_SLOTS.map(function (s) {
      const isChosen = s.id === chosenSlotId;
      const choice = voteState[s.id] || '';
      return {
        id: s.id,
        start: s.start,
        end: s.end,
        backgroundColor: choiceColor(choice, isChosen),
        borderColor: isChosen ? '#5b21b6' : choiceColor(choice, false),
        textColor: '#ffffff',
        extendedProps: { slotId: s.id, isChosen: isChosen },
      };
    });
  }

  function renderEventContent(info) {
    const slotId = info.event.extendedProps.slotId;
    const isChosen = info.event.extendedProps.isChosen;
    const choice = voteState[slotId] || '';
    const viewType = info.view.type;

    // Month view: compact single-line with explicit background color
    // (dayGridMonth renders timed events as dot+text, backgroundColor not shown as block)
    if (viewType === 'dayGridMonth') {
      const icon = isChosen ? '★' : choice === 'yes' ? '✓' : choice === 'maybe' ? '?' : choice === 'no' ? '✗' : '';
      const el = document.createElement('div');
      el.className = 'fc-vote-compact';
      el.title = !isClosed ? 'Cliquez pour voter' : '';
      el.style.backgroundColor = info.event.backgroundColor;
      const timeSpan = document.createElement('span');
      timeSpan.className = 'fc-vote-compact-time';
      timeSpan.textContent = info.timeText;
      el.appendChild(timeSpan);
      if (icon) {
        const iconSpan = document.createElement('span');
        iconSpan.className = 'fc-vote-compact-icon';
        iconSpan.textContent = ' ' + icon;
        el.appendChild(iconSpan);
      }
      return { domNodes: [el] };
    }

    // Week/day views: full layout with vote icon buttons
    const container = document.createElement('div');
    container.className = 'fc-vote-event';

    const timeEl = document.createElement('span');
    timeEl.className = 'fc-event-time-custom';
    timeEl.textContent = info.timeText;
    container.appendChild(timeEl);

    if (isChosen) {
      const badge = document.createElement('span');
      badge.className = 'fc-chosen-badge';
      badge.textContent = '★';
      container.appendChild(badge);
    }

    if (!isClosed) {
      const icons = document.createElement('div');
      icons.className = 'fc-vote-icons';

      [
        { value: 'yes', label: '✓', cls: 'icon-yes' },
        { value: 'maybe', label: '?', cls: 'icon-maybe' },
        { value: 'no', label: '✗', cls: 'icon-no' },
      ].forEach(function (opt) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'vote-icon ' + opt.cls + (choice === opt.value ? ' active' : '');
        btn.textContent = opt.label;
        btn.title = opt.value === 'yes' ? 'Oui' : opt.value === 'maybe' ? 'Peut-être' : 'Non';
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          voteState[slotId] = opt.value;
          calendar.refetchEvents();
        });
        icons.appendChild(btn);
      });

      container.appendChild(icons);
    }

    return { domNodes: [container] };
  }

  // Month view: click cycles through vote states (no buttons visible)
  function handleEventClick(info) {
    if (info.view.type !== 'dayGridMonth') return;
    if (isClosed) return;
    info.jsEvent.preventDefault();
    const slotId = info.event.extendedProps.slotId;
    const current = voteState[slotId] || '';
    const cycle = { '': 'yes', 'yes': 'maybe', 'maybe': 'no', 'no': '' };
    voteState[slotId] = cycle[current];
    calendar.refetchEvents();
  }

  const calendarEl = document.getElementById('calendar');
  const isMobile = window.innerWidth < 768;

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: isMobile ? 'listWeek' : 'timeGridWeek',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: isMobile ? 'listWeek,timeGridDay' : 'timeGridWeek,dayGridMonth',
    },
    locale: 'fr',
    firstDay: 1,
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    allDaySlot: false,
    editable: false,
    selectable: false,
    // Use function-based event source with FullCalendar v6 callback API
    events: function (fetchInfo, successCallback) {
      successCallback(buildEvents());
    },
    eventContent: renderEventContent,
    eventClick: handleEventClick,
  });

  calendar.render();

  // Jump to first event date
  if (POLL_SLOTS.length > 0) {
    calendar.gotoDate(POLL_SLOTS[0].start);
  }

  // Save button handler
  const saveBtn = document.getElementById('save-votes');
  if (saveBtn) {
    saveBtn.addEventListener('click', function () {
      const statusEl = document.getElementById('save-status');
      statusEl.textContent = 'Enregistrement…';
      statusEl.className = 'save-status saving';

      fetch(VOTE_SUBMIT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN,
        },
        body: JSON.stringify({ votes: voteState }),
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.status === 'ok') {
            statusEl.textContent = 'Votes enregistrés !';
            statusEl.className = 'save-status saved';
          } else {
            statusEl.textContent = data.error || 'Erreur lors de l\'enregistrement.';
            statusEl.className = 'save-status error';
          }
        })
        .catch(function () {
          statusEl.textContent = 'Erreur réseau. Veuillez réessayer.';
          statusEl.className = 'save-status error';
        });
    });
  }

  // Responsive: listen for window resize
  window.addEventListener('resize', function () {
    const mobile = window.innerWidth < 768;
    if (mobile && calendar.view.type !== 'listWeek' && calendar.view.type !== 'timeGridDay') {
      calendar.changeView('listWeek');
    }
  });
})();
