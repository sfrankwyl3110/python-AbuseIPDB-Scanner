from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, PasswordField, BooleanField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, Email


class UploadForm(FlaskForm):
    action = "/upload"
    file = FileField('Select file', validators=[DataRequired()])
    submit = SubmitField('Upload')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = '/pdf' + self.action
        

class TokenForm(FlaskForm):
    action = "/try_2fa"
    username = StringField('User')
    token = StringField('Token', validators=[DataRequired(), Length(6, 6)])
    submit = SubmitField()
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BootswatchForm(FlaskForm):
    theme_name = RadioField(
        default='default',
        choices=[
            ('default', 'none'),
            ('cerulean', 'Cerulean 5.1.3'),
            ('cosmo', 'Cosmo 5.1.3'),
            ('cyborg', 'Cyborg 5.1.3'),
            ('darkly', 'Darkly 5.1.3'),
            ('flatly', 'Flatly 5.1.3'),
            ('journal', 'Journal 5.1.3'),
            ('litera', 'Litera 5.1.3'),
            ('lumen', 'Lumen 5.1.3'),
            ('lux', 'Lux 5.1.3'),
            ('materia', 'Materia 5.1.3'),
            ('minty', 'Minty 5.1.3'),
            ('morph', 'Morph 5.1.3'),
            ('pulse', 'Pulse 5.1.3'),
            ('quartz', 'Quartz 5.1.3'),
            ('sandstone', 'Sandstone 5.1.3'),
            ('simplex', 'Simplex 5.1.3'),
            ('sketchy', 'Sketchy 5.1.3'),
            ('slate', 'Slate 5.1.3'),
            ('solar', 'Solar 5.1.3'),
            ('spacelab', 'Spacelab 5.1.3'),
            ('superhero', 'Superhero 5.1.3'),
            ('united', 'United 5.1.3'),
            ('vapor', 'Vapor 5.1.3'),
            ('yeti', 'Yeti 5.1.3'),
            ('zephyr', 'Zephyr 5.1.3'),
        ]
    )
    submit = SubmitField()


class RegisterForm(FlaskForm):
    action = "/register"
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 128)])
    password = PasswordField('Password', validators=[DataRequired()])
    password_again = PasswordField('Password again',
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class LoginForm(FlaskForm):
    action = "/login"
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(4, 150)])
    token = StringField('Token', validators=[DataRequired(), Length(6, 6)])
    remember = BooleanField('Remember me')
    submit = SubmitField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
