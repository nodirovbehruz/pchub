(function($) {
    'use strict';
    
    $(document).ready(function() {
        const pathField = $('#id_executable_path');
        if (!pathField.length) return;

        // Create browse button
        const browseBtn = $('<button type="button" class="button" style="margin-left: 10px; background: #79aec8; color: white;">Обзор...</button>');
        pathField.after(browseBtn);

        // Modal structure
        const modalHtml = `
            <div id="file-browser-modal" style="display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.5);">
                <div style="background:white; margin:5% auto; padding:20px; border-radius:8px; width:60%; max-height:80%; overflow-y:auto; box-shadow:0 4px 20px rgba(0,0,0,0.2);">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:15px;">
                        <h3 style="margin:0;">Выбор исполняемого файла (.exe)</h3>
                        <span id="close-browser" style="cursor:pointer; font-size:24px; font-weight:bold;">&times;</span>
                    </div>
                    <div id="current-path-display" style="background:#f8f9fa; padding:8px; border-radius:4px; margin-bottom:10px; font-family:monospace; word-break:break-all;"></div>
                    <div id="file-list" style="display:flex; flex-direction:column; gap:4px;"></div>
                </div>
            </div>
        `;
        $('body').append(modalHtml);

        const modal = $('#file-browser-modal');
        const fileList = $('#file-list');
        const pathDisplay = $('#current-path-display');

        browseBtn.on('click', function() {
            modal.show();
            loadFiles(pathField.val() || '');
        });

        $('#close-browser').on('click', function() {
            modal.hide();
        });

        function loadFiles(path) {
            fileList.html('<p>Загрузка...</p>');
            
            // Extract directory from path if it's a file
            let dirPath = path;
            if (path && !path.endsWith('\\') && !path.endsWith('/')) {
                const parts = path.split(/[\\/]/);
                parts.pop();
                dirPath = parts.join('\\') + '\\';
            }

            $.ajax({
                url: '/api/v1/games/browse-files/',
                data: { path: dirPath },
                headers: {
                    'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
                },
                success: function(data) {
                    pathDisplay.text(data.current_path || 'Список дисков');
                    fileList.empty();

                    data.items.forEach(item => {
                        const icon = item.is_dir ? '📁' : '🎮';
                        const color = item.is_dir ? '#007bff' : '#28a745';
                        const itemBtn = $(`
                            <div style="padding:8px; border:1px solid #eee; border-radius:4px; cursor:pointer; display:flex; align-items:center; gap:10px; transition:background 0.2s;">
                                <span style="font-size:18px;">${icon}</span>
                                <span style="flex-grow:1; color:${color}; font-weight:${item.is_dir ? 'bold' : 'normal'}">${item.name}</span>
                                ${!item.is_dir ? '<small style="color:#666">' + (item.size / 1024 / 1024).toFixed(2) + ' MB</small>' : ''}
                            </div>
                        `);

                        itemBtn.hover(
                            function() { $(this).css('background', '#f0f7ff'); },
                            function() { $(this).css('background', 'white'); }
                        );

                        itemBtn.on('click', function() {
                            if (item.is_dir) {
                                loadFiles(item.path);
                            } else {
                                pathField.val(item.path);
                                modal.hide();
                                // Try to auto-fill name if empty
                                const nameField = $('#id_name');
                                if (!nameField.val()) {
                                    nameField.val(item.name.replace('.exe', ''));
                                }
                                // Switch game type to LOCAL
                                $('#id_game_type').val('local');
                            }
                        });

                        fileList.append(itemBtn);
                    });
                },
                error: function() {
                    fileList.html('<p style="color:red;">Ошибка загрузки. Проверьте права доступа.</p>');
                }
            });
        }
    });
})(django.jQuery);
