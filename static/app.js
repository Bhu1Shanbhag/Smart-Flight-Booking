document.addEventListener('DOMContentLoaded', () => {
    // Stepper Navigation Visual Update
    const updateStepper = (stepNum) => {
        document.querySelectorAll('.step-item').forEach((item) => {
            const num = parseInt(item.getAttribute('data-step'));
            if (num <= stepNum) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    };

    const showStep = (stepId) => {
        document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));
        const activeElem = document.getElementById(stepId);
        if (activeElem) {
            activeElem.classList.add('active');
        }

        // Map stepId to step number
        const stepMap = {
            'step-1': 1,
            'step-2': 2,
            'step-3': 3,
            'step-loading': 3,
            'step-4': 4
        };
        if (stepMap[stepId]) {
            updateStepper(stepMap[stepId]);
        }
    };

    // Default Date setup to tomorrow
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        dateInput.value = tomorrow.toISOString().split('T')[0];
    }

    // Date Shortcuts
    const setDateOffset = (days) => {
        const d = new Date();
        d.setDate(d.getDate() + days);
        if (dateInput) {
            dateInput.value = d.toISOString().split('T')[0];
        }
    };

    document.getElementById('chip-today')?.addEventListener('click', () => setDateOffset(0));
    document.getElementById('chip-tomorrow')?.addEventListener('click', () => setDateOffset(1));
    document.getElementById('chip-nextweek')?.addEventListener('click', () => setDateOffset(7));

    // Swap Cities
    document.getElementById('btn-swap-cities')?.addEventListener('click', () => {
        const oCity = document.getElementById('origin_city');
        const oLoc = document.getElementById('origin_loc');
        const dCity = document.getElementById('destination_city');
        const dLoc = document.getElementById('destination_loc');

        const tempCity = oCity.value;
        const tempLoc = oLoc.value;

        oCity.value = dCity.value;
        oLoc.value = dLoc.value;

        dCity.value = tempCity;
        dLoc.value = tempLoc;
    });

    // Popular Route Quick-Select
    window.selectRoute = (originCity, originLoc, destCity, destLoc) => {
        document.getElementById('origin_city').value = originCity;
        document.getElementById('origin_loc').value = originLoc;
        document.getElementById('destination_city').value = destCity;
        document.getElementById('destination_loc').value = destLoc;

        document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' });
    };

    // Quick Feedback Handler
    window.quickFeedback = (text) => {
        const input = document.getElementById('feedback-input');
        if (input) {
            input.value = text;
            document.getElementById('submit-feedback').click();
        }
    };

    // Hours Controls
    const hoursInput = document.getElementById('meeting_hours');
    document.getElementById('btn-dec-hours')?.addEventListener('click', () => {
        if (hoursInput) {
            const val = parseFloat(hoursInput.value) || 2;
            if (val > 0.5) hoursInput.value = (val - 0.5).toFixed(1);
        }
    });

    document.getElementById('btn-inc-hours')?.addEventListener('click', () => {
        if (hoursInput) {
            const val = parseFloat(hoursInput.value) || 2;
            hoursInput.value = (val + 0.5).toFixed(1);
        }
    });

    window.setHours = (h) => {
        if (hoursInput) hoursInput.value = h;
    };

    // Step 1: Submit Travel Request
    document.getElementById('travel-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = e.target.querySelector('button[type="submit"]');
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<span>Analyzing Weather & Route...</span> <i class="fa-solid fa-spinner fa-spin"></i>';
        btn.disabled = true;

        const payload = {
            origin_city: document.getElementById('origin_city').value,
            origin_loc: document.getElementById('origin_loc').value,
            destination_city: document.getElementById('destination_city').value,
            destination_loc: document.getElementById('destination_loc').value,
            date: document.getElementById('date').value,
            meeting_time: document.getElementById('meeting_time').value,
            return_required: document.getElementById('return_required').checked
        };

        try {
            const res = await fetch('/api/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            updateStrategyUI(data.strategy);
            showStep('step-2');
        } catch (err) {
            console.error(err);
            alert("Failed to connect to AI planner system.");
        } finally {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    });

    const updateStrategyUI = (strategy) => {
        document.getElementById('strat-leave').innerText = strategy.leave_office || '--:--';
        document.getElementById('strat-airport').innerText = strategy.reach_airport || '--:--';
        document.getElementById('strat-depart').innerText = strategy.flight_departure || '--:--';
        document.getElementById('strat-arrive').innerText = strategy.flight_arrival || '--:--';
        document.getElementById('strat-venue').innerText = strategy.expected_arrival_at_venue || '--:--';
        document.getElementById('strat-reasoning').innerText = strategy.reason || 'Optimal route buffer times calculated.';
    };

    // Step 2: Submit Feedback
    document.getElementById('submit-feedback')?.addEventListener('click', async () => {
        const input = document.getElementById('feedback-input').value;
        if (!input) return;

        const btn = document.getElementById('submit-feedback');
        const originalText = btn.innerText;
        btn.innerText = 'Processing...';
        btn.disabled = true;

        try {
            const res = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feedback: input })
            });
            const data = await res.json();
            
            if (data.status === 'approved') {
                showStep('step-3');
            } else {
                updateStrategyUI(data.strategy);
                document.getElementById('feedback-input').value = '';
            }
        } catch (err) {
            console.error(err);
            alert("Failed to process constraint feedback.");
        } finally {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    });

    // Step 3: Submit Duration & Trigger Booking
    document.getElementById('submit-duration')?.addEventListener('click', async () => {
        const hours = document.getElementById('meeting_hours').value;
        
        const btn = document.getElementById('submit-duration');
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<span>Initiating Agent Swarm...</span> <i class="fa-solid fa-spinner fa-spin"></i>';
        btn.disabled = true;

        try {
            await fetch('/api/duration', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meeting_hours: hours })
            });
            
            // Move to loading screen
            showStep('step-loading');
            
            // Trigger actual booking search
            const bookRes = await fetch('/api/book', {
                method: 'POST'
            });
            const bookData = await bookRes.json();
            
            if (bookData.error) {
                alert(bookData.error);
                showStep('step-3');
                return;
            }
            
            displayFinalItinerary(bookData.itinerary);
            showStep('step-4');

        } catch (err) {
            console.error(err);
            alert("Failed to generate flight & hotel bookings.");
            showStep('step-3');
        } finally {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    });

    const displayFinalItinerary = (itinerary) => {
        // Flight
        const flight = itinerary.flight || {};
        const isRoundTrip = !!(flight.return_departure || flight.return_arrival);

        // Outbound leg
        document.getElementById('res-airline').innerText = flight.airline || 'N/A';
        document.getElementById('res-outbound-departure').innerText = flight.outbound_departure || flight.departure_time || '--';
        document.getElementById('res-outbound-arrival').innerText = flight.outbound_arrival || flight.arrival_time || '--';

        // Return leg — show or hide the entire row
        const returnRow = document.getElementById('return-leg-row');
        if (isRoundTrip && returnRow) {
            returnRow.style.display = 'block';
            document.getElementById('res-return-airline').innerText = flight.return_airline || flight.airline || 'N/A';
            document.getElementById('res-return-departure').innerText = flight.return_departure || '--';
            document.getElementById('res-return-arrival').innerText = flight.return_arrival || '--';
        } else if (returnRow) {
            returnRow.style.display = 'none';
        }

        document.getElementById('res-flight-price').innerText = `₹${flight.price ? Number(flight.price).toLocaleString('en-IN') : '0'}`;
        document.getElementById('res-flight-reason').innerText = flight.reason || '';
        
        const flightLink = document.getElementById('res-flight-link');
        if (flightLink) {
            flightLink.href = itinerary.flight_link || '#';
        }

        // Hotel
        const hotel = itinerary.hotel;
        const hotelContainer = document.getElementById('hotel-card-container');
        if (hotel && hotelContainer) {
            hotelContainer.style.display = 'block';
            document.getElementById('res-hotel-name').innerText = hotel.hotel_name || 'Executive Hotel';
            document.getElementById('res-hotel-price').innerText = `₹${hotel.estimated_cost_per_night || '0'}`;
            document.getElementById('res-hotel-reason').innerText = hotel.reason || 'Selected for proximity to venue & corporate comfort.';
            
            const hotelLink = document.getElementById('res-hotel-link');
            if (hotelLink) {
                hotelLink.href = itinerary.hotel_link || '#';
            }
        } else if (hotelContainer) {
            hotelContainer.style.display = 'none';
        }

        // Costs
        const costs = itinerary.estimated_costs || {};
        const totalVal = costs.total_estimated_cost ? costs.total_estimated_cost.toLocaleString('en-IN') : '0';
        document.getElementById('res-total-cost').innerText = `₹${totalVal} ${costs.currency || 'INR'}`;
    };

    // Restart & New Trip Buttons
    const resetPlanner = () => {
        document.getElementById('travel-form')?.reset();
        setDateOffset(1);
        showStep('step-1');
        document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' });
    };

    document.getElementById('btn-restart')?.addEventListener('click', resetPlanner);
    document.getElementById('quick-reset-btn')?.addEventListener('click', resetPlanner);
});
