import os
import platform
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
import string

class FileBrowserAPIView(APIView):
    """
    API for browsing local server files in the Django Admin.
    Allows selecting .exe files for local games.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        path = request.query_params.get('path', '')
        
        # If no path, return list of available drives (Windows)
        if not path:
            if platform.system() == 'Windows':
                drives = []
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append({
                            'name': drive,
                            'path': drive,
                            'is_dir': True,
                            'type': 'drive'
                        })
                return Response({'current_path': '', 'items': drives})
            else:
                path = '/'

        try:
            if not os.path.exists(path):
                return Response({'error': 'Path not found'}, status=status.HTTP_404_NOT_FOUND)

            items = []
            
            # Add "back" item
            parent = os.path.dirname(path.rstrip('\\/'))
            if parent and parent != path:
                items.append({
                    'name': '.. [Parent Directory]',
                    'path': parent,
                    'is_dir': True,
                    'type': 'parent'
                })

            # List directory contents
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        # Skip hidden files
                        if entry.name.startswith('$') or entry.name.startswith('.'):
                            continue
                            
                        is_dir = entry.is_dir()
                        is_exe = entry.name.lower().endswith('.exe')
                        
                        if is_dir or is_exe:
                            items.append({
                                'name': entry.name,
                                'path': entry.path,
                                'is_dir': is_dir,
                                'type': 'dir' if is_dir else 'exe',
                                'size': entry.stat().st_size if not is_dir else 0
                            })
                    except (PermissionError, OSError):
                        continue

            # Sort: dirs first, then files
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

            return Response({
                'current_path': path,
                'items': items
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
