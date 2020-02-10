import datetime
import os
import io
import hashlib
from shutil import copyfile

from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from django.db.models import signals

from PIL import Image

from avatar.util import invalidate_cache
from avatar.settings import (AVATAR_STORAGE_DIR, AVATAR_RESIZE_METHOD,
                             AVATAR_MAX_AVATARS_PER_USER, AVATAR_THUMB_FORMAT,
                             AVATAR_HASH_USERDIRNAMES, AVATAR_HASH_FILENAMES,
                             AVATAR_THUMB_QUALITY, AUTO_GENERATE_AVATAR_SIZES)


def avatar_file_path(instance=None, filename=None, size=None, ext=None):
    tmppath = [AVATAR_STORAGE_DIR]
    if AVATAR_HASH_USERDIRNAMES:
        tmp = hashlib.md5(instance.user.username).hexdigest()
        tmppath.extend([tmp[0], tmp[1], instance.user.username])
    else:
        tmppath.append(instance.user.username)
    if not filename:
        # Filename already stored in database
        filename = instance.avatar.name
        if ext and AVATAR_HASH_FILENAMES:
            # An extension was provided, probably because the thumbnail
            # is in a different format than the file. Use it. Because it's
            # only enabled if AVATAR_HASH_FILENAMES is true, we can trust
            # it won't conflict with another filename
            (root, oldext) = os.path.splitext(filename)
            filename = root + "." + ext
    else:
        # File doesn't exist yet
        if AVATAR_HASH_FILENAMES:
            (root, ext) = os.path.splitext(filename)
            filename = hashlib.md5(smart_str(filename)).hexdigest()
            filename = filename + ext
    if size:
        tmppath.extend(['resized', str(size)])
    tmppath.append(os.path.basename(filename))
    return os.path.join(*tmppath)

def find_extension(format):
    format = format.lower()

    if format == 'jpeg':
        format = 'jpg'

    return format

class Avatar(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    primary = models.BooleanField(default=False)
    avatar = models.ImageField(max_length=1024, upload_to=avatar_file_path, blank=True)
    date_uploaded = models.DateTimeField(default=datetime.datetime.now)
    
    def __str__(self):
        return _("Avatar for %s") % self.user
    
    def save(self, *args, **kwargs):
        avatars = Avatar.objects.filter(user=self.user)
        if self.pk:
            avatars = avatars.exclude(pk=self.pk)
        if AVATAR_MAX_AVATARS_PER_USER > 1:
            if self.primary:
                avatars = avatars.filter(primary=True)
                avatars.update(primary=False)
        else:
            avatars.delete()
        invalidate_cache(self.user)
        super(Avatar, self).save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        invalidate_cache(self.user)
        super(Avatar, self).delete(*args, **kwargs)
    
    def thumbnail_exists(self, size):
        return self.avatar.storage.exists(self.avatar_name(size))
    
    def create_thumbnail(self, size, quality=None):
        # invalidate the cache of the thumbnail with the given size first
        invalidate_cache(self.user, size)
        try:
            image = Image.open(self.avatar.name)
        except IOError:
            return # What should we do here?  Render a "sorry, didn't work" img?
        quality = quality or AVATAR_THUMB_QUALITY
        (w, h) = image.size
        if w != size or h != size:
            if w > h:
                diff = (w - h) / 2
                image = image.crop((diff, 0, w - diff, h))
            else:
                diff = (h - w) / 2
                image = image.crop((0, diff, w, h - diff))
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = image.resize((size, size), AVATAR_RESIZE_METHOD)
            thumb = io.BytesIO()
            image.save(thumb, AVATAR_THUMB_FORMAT, quality=quality)
            thumb_file = ContentFile(thumb.getvalue())
        else:
            thumb_file = ContentFile(orig)
        thumb = self.avatar.storage.save(self.avatar_name(size), thumb_file)

    def avatar_url(self, size):
        try:
            _base_path = os.path.split(self.avatar_name(size))[0]
            _upload_path = os.path.split(
                self.avatar.storage.url(self.avatar_name(size)))[1]
            _upload_path = os.path.join(_base_path, _upload_path)
            if not self.avatar.storage.exists(_upload_path):
                copyfile(self.avatar.storage.path(self.avatar_name(size)),
                         self.avatar.storage.path(_upload_path))
        except BaseException:
            pass
        return self.avatar.storage.url(self.avatar_name(size))
    
    def avatar_name(self, size):
        ext = find_extension(AVATAR_THUMB_FORMAT)
        return avatar_file_path(
            instance=self,
            size=size,
            ext=ext
        )


def create_default_thumbnails(instance=None, created=False, **kwargs):
    if created:
        for size in AUTO_GENERATE_AVATAR_SIZES:
            instance.create_thumbnail(size)

signals.post_save.connect(create_default_thumbnails, sender=Avatar)
