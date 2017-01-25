function track_quicklook(file)
    f = figure(1); clf
    f.WindowStyle = 'docked';
    img = proc_one_file(file);
    x = double(get_audio(file))/2^15;
    fs = 44100;
    player = audioplayer(x, fs);

    time = img.YData;
    wf = img.CData;
    idx = 0;
    n_sec_per_win = 10;
    n_sec_per_frm = n_sec_per_win;
    t0 = 0;
    f_win = @(t0, time) and(time >= t0, time < t0 + n_sec_per_win);
    f_minmax = @(x) [min(x), max(x)];
    t_start = now;
    f_elapsed = @(t1) t1 - t_start;
    while t0 < max(time) - n_sec_per_win
        idx = f_win(t0, time);
        time_win = time(idx);
        img.Parent.YLim = f_minmax(time_win);
        img.YData = time_win;
        img.CData = wf(idx, :);
        drawnow;
        player.play(round([t0, t0 + n_sec_per_frm]*fs) + 1);
        t0 = t0 + n_sec_per_frm;
        while t0 > f_elapsed(now); pause(0.1); fprintf('t0: %.2f, elapsed: %.2f\n', t0, f_elapsed(now)); end
    end
end

function z = get_audio(file)
    fid = fopen(file);
    z = fread(fid, '*int16');
    fclose(fid);
    z = z(1:2:end); % keep only one channel
    if isrow(z); z = z(:); end
end

function img = proc_one_file(file)
    fs = 44100;
    win_duration = 0.01;
    overlap_duration = 0.000;
    n_spw = round(win_duration*fs);
    n_fft = 2*n_spw;
    df = fs/n_fft;
    f_max_samp = round(n_fft/16) - 1;
    f_max = f_max_samp*df;
    n_spo = round(overlap_duration*fs);

    % prepare process
    x = double(get_audio(file));
    n_samp = length(x);
    n_win = floor(n_samp/n_spw);
    dt = (n_spw + n_spo)/fs;
    t = 0:dt:n_spw*n_win/fs;
    x = x(1:n_spw*n_win);
    x = reshape(x, [n_spw, n_win]);
    x = [x;
        circshift(...       % crate overlpa matrix
        x(1:n_spo, :), ...  % the overlap data
        [0, -1])...         % align with previous column
        ];
    w = repmat(hanning(n_spw + n_spo)', size(x, 2), 1).';
    x = fft(w.*x, n_fft, 1); % Fourier transform
    x = x(1:f_max_samp, :); % truncate to audible spectrum
    x = 20*log10(abs(x)).'; % dB
    f = 0:df:f_max;
    img = imagesc(f/1000, t, x);
    ylabel('slow time [sec]'); xlabel('spectrum [kHz]');
    colorbar; colormap hot; caxis([40, 130]);
end
