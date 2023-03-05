function run_manager() {
    $.ajax({
        url: "/run",
        type: "POST",
        statusCode: {
            404: function() {
            }
        },
        success: function(data) {
            console.log(data)
        }
    })
}

function scrollToBottom(divId) {
    const div = document.getElementById(divId);
    div.scrollTop = div.scrollHeight;
}


if (window.location.protocol == "https:"){
    let ws_scheme = "wss://";
}else{
    let ws_scheme = "ws://";
} 


let socket = io("ws://" + location.host);

    let interval;
    let show_login = false
    let last_enabled = false;

    $(document).ready(function() {

        $.ajax({
                url: "toggle_2fa",
                success: function(data) {
                    if(!data["enabled"]) {
                        if(!$("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked')) {
                            $("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked', true)
                        }
                    } else {

                        $("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked', false)
                         $("input[name='options-outlined'][id='enabled-outlined']").prop('checked', 'checked')
                    }

                }

            })

        $("#btn_run").on('click', function(ev) {
            ev.preventDefault();
            run_manager()
        })
        socket.on('connect', function() {
            socket.emit('my_event', {data: 'I\'m connected!'});
        });

        socket.on('my_response', function(msg, cb) {
            $('#log').append('<br>' + $('<div/>').text(new Date().toLocaleString()+': ' + msg.data).html());
            if (cb)
                cb();
            scrollToBottom("log")

        });

        // Interval function that tests message latency by sending a "ping"
        // message. The server then responds with a "pong" message and the
        // round trip time is measured.
        var ping_pong_times = [];
        var start_time;
        window.setInterval(function() {
            start_time = (new Date).getTime();
            $('#transport').text(socket.io.engine.transport.name);
            socket.emit('my_ping');
        }, 1000);

        // Handler for the "pong" message. When the pong is received, the
        // time from the ping is stored, and the average of the last 30
        // samples is average and displayed.
        socket.on('my_pong', function() {
            var latency = (new Date()).getTime() - start_time;
            ping_pong_times.push(latency);
            ping_pong_times = ping_pong_times.slice(-30); // keep last 30 samples
            var sum = 0;
            for (var i = 0; i < ping_pong_times.length; i++)
                sum += ping_pong_times[i];
            $('#ping-pong').text(Math.round(10 * sum / ping_pong_times.length) / 10);
        });
        socket.on('my_login_response', function(msg, cb) {
            $('#log').append('<br>' + $('<div/>').text(new Date().toLocaleString()+': ' + msg.data).html());
            if (cb)
                cb();
            scrollToBottom("log")

        });

        $("#toggle_2fa_enabled").on('click', function(ev) {
                ev.preventDefault()
            $.ajax({
                url: "toggle_2fa",
                data: {
                    enabled: last_enabled
                },
                method: "POST",
                success: function(data) {
                     if(!data["enabled"]) {
                        if(!$("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked')) {
                            $("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked', true)
                        }
                    } else {
                        $("input[name='options-outlined'][id='not-enabled-outlined']").prop('checked', false)
                         $("input[name='options-outlined'][id='enabled-outlined']").prop('checked', 'checked')
                    }
                }

            })
        })
    })