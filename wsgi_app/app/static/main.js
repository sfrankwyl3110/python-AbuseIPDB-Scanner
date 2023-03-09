let al = 2;
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

function basename(path) {

    if  (path.split('/').reverse()[0] == path) {
        return path.split('\\').reverse()[0]
    } else {
        return path.split('/').reverse()[0]
    }
    return path.split('/').reverse()[0];
}

function create_new_div(message) {
    let new_Div = document.createElement('div')
    $(new_Div).addClass('row')
    $(new_Div).attr('data-ident', 'error_row')
    let new_Div_ = document.createElement('div')
    $(new_Div_).addClass("col-12")
    $(new_Div).append(new_Div_)
    $(new_Div_).html(new Date().toLocaleString()+": "+basename($("#file").val())+" "+message)
    return new_Div_
}

function scrollToBottom(divId) {
    const div = document.getElementById(divId);
    div.scrollTop = div.scrollHeight;
}

function date_from_ts(timestamp) {
    return new Date(timestamp * 1000);
}

function formatted_date_from_ts(timestamp) {
    let date = new Date(timestamp * 1000);
    // Get the individual components of the date and time
    const day = date.getDate();
    const month = date.getMonth() + 1; // Note: Month starts from 0
    const year = date.getFullYear();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const seconds = date.getSeconds();
    const milliseconds = date.getMilliseconds();

// Format the date string with the components
    const formattedDate = `${day < 10 ? '0' + day : day}.${month < 10 ? '0' + month : month}.${year} ${hours < 10 ? '0' + hours : hours}:${minutes < 10 ? '0' + minutes : minutes}:${seconds < 10 ? '0' + seconds : seconds}.${milliseconds < 10 ? '00' + milliseconds : milliseconds < 100 ? '0' + milliseconds : milliseconds}`;
    return formattedDate
}


if (window.location.protocol == "https:"){
    let ws_scheme = "wss://";
}else{
    let ws_scheme = "ws://";
}


function get_files_at_ready(files_url, delete_url) {

    $.ajax({
        url: files_url,
        success: function (data) {
            console.log(Object.keys(data["files"]))
            $.each(Object.keys(data["files"]), function (index, current_file) {
                console.log(data["files"][current_file]["st_mtime"])
                console.log(formatted_date_from_ts(data["files"][current_file]["st_mtime"]))
                console.log(data["files"][current_file]["st_ctime"])
                console.log(data["files"][current_file]["st_size"])
                let li_element = document.createElement('li')
                let del_btn = $('<input type="button" value="del">');
                del_btn.className = "btn-primary"
                $(li_element).html(current_file)
                $(li_element).append($(del_btn))
                $(del_btn).on('click', function (ev) {
                    ev.preventDefault();
                    $.ajax({
                        url: delete_url,
                        type: "POST",
                        data: {
                            file: current_file
                        },
                        success: function (data) {
                            if(!data["success"] && data["exists_"]) {
                                console.log("EXISTING FILE, confirm for removal")
                                if (window.confirm("Do you really want to delete "+current_file+"?")) {
                                    $.ajax({
                                        url: delete_url,
                                        type: "POST",
                                        data: {
                                            file: current_file,
                                            confirmed: true
                                        },
                                        success: function (data) {
                                            if(data["success"]) {
                                                $("#ufiles").remove($(li_element))
                                                window.location.reload()
                                            }

                                        }
                                    })
                                }
                            }
                        }
                    })
                })
                $("#ufiles").append($(li_element))


            })
        }
    })
}


let socket = io("ws://" + location.host);

    let interval;
    let show_login = false
    let last_enabled = false;

    $(function() {



        const currentUrl = window.location.href;
        // Create a new instance of URLSearchParams with the query string of the current URL
        const searchParams = new URLSearchParams(currentUrl.split('?')[1]);
        if (searchParams.get('login') == "True") {
            $("#login_container").toggleClass('hide_login show_login');
        }

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
        $("#btn_run_extraction").on('click', function (ev) {
            ev.preventDefault()
            $.ajax({
                url: '/run_extraction',
                success: function (data) {
                    console.log(data)
                }
            })
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