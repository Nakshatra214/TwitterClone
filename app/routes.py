from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
import os
from . import db
from .models import User, Tweet, Retweet, Like
from .forms import LoginForm, RegistrationForm, TweetForm, EditProfileForm
from datetime import datetime

# Helper function to check if a user has retweeted a tweet
def has_retweeted(user, tweet_id):
    return Retweet.query.filter_by(user_id=user.id, tweet_id=tweet_id).count() > 0

def init_routes(app):
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('home.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Login Unsuccessful. Please check email and password', 'danger')
        return render_template('login.html', form=form)

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        return render_template('signup.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('home'))

    @app.route('/dashboard', methods=['GET', 'POST'])
    @login_required
    def dashboard():
        form = TweetForm()
        if form.validate_on_submit():
            try:
                tweet = Tweet(content=form.content.data, author=current_user)
                if form.image.data:
                    image = form.image.data
                    filename = secure_filename(image.filename)
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tweets', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    image.save(filepath)
                    tweet.image = filename
                db.session.add(tweet)
                db.session.commit()
                
                # Check if it's an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': 'Tweet posted successfully!',
                        'tweet': {
                            'id': tweet.id,
                            'content': tweet.content,
                            'author': {
                                'username': tweet.author.username,
                                'profile_image': tweet.author.profile_image
                            },
                            'image': tweet.image if tweet.image else None,
                            'created_at': tweet.created_at.strftime('%b %d'),
                            'likes_count': 0,
                            'retweets_count': 0
                        }
                    })
                
                flash('Your tweet has been posted!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': 'Error posting tweet. Please try again.'
                    }), 500
                flash('Error posting tweet. Please try again.', 'danger')
                return redirect(url_for('dashboard'))
        
        # Get tweets from the current user and people they follow
        followed_tweets = Tweet.query.join(
            User, (User.id == Tweet.user_id)
        ).filter(
            User.id.in_([user.id for user in current_user.following] + [current_user.id])
        ).order_by(Tweet.created_at.desc()).all()
        
        # Get suggested users (users that the current user is not following)
        suggested_users = User.query.filter(
            User.id != current_user.id,
            ~User.followers.any(id=current_user.id)
        ).limit(5).all()
        
        if form.errors and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'errors': form.errors
            }), 400
            
        return render_template('dashboard.html', form=form, tweets=followed_tweets, suggested_users=suggested_users, has_retweeted=has_retweeted)

    @app.route('/profile/<username>')
    @login_required
    def profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        tweets = Tweet.query.filter_by(user_id=user.id).order_by(Tweet.created_at.desc()).all()
        
        # Get suggested users (excluding current user and profile user)
        suggested_users = User.query.filter(
            User.id != current_user.id,
            User.id != user.id,
            ~User.followers.any(id=current_user.id)
        ).limit(5).all()
        
        return render_template('profile.html', user=user, tweets=tweets, suggested_users=suggested_users, has_retweeted=has_retweeted)

    @app.route('/edit_profile', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        form = EditProfileForm(original_username=current_user.username)
        if form.validate_on_submit():
            current_user.username = form.username.data
            current_user.email = form.email.data
            current_user.bio = form.bio.data
            current_user.location = form.location.data
            current_user.website = form.website.data
            if form.profile_image.data:
                filename = secure_filename(form.profile_image.data.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_pics', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                form.profile_image.data.save(filepath)
                current_user.profile_image = filename
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('profile', username=current_user.username))
        elif request.method == 'GET':
            form.username.data = current_user.username
            form.email.data = current_user.email
            form.bio.data = current_user.bio
            form.location.data = current_user.location
            form.website.data = current_user.website
        return render_template('edit_profile.html', form=form)

    @app.route('/follow/<username>')
    @login_required
    def follow(username):
        user = User.query.filter_by(username=username).first_or_404()
        if user == current_user:
            flash('You cannot follow yourself!', 'danger')
            return redirect(url_for('profile', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are now following {username}!', 'success')
        return redirect(url_for('profile', username=username))

    @app.route('/unfollow/<username>')
    @login_required
    def unfollow(username):
        user = User.query.filter_by(username=username).first_or_404()
        if user == current_user:
            flash('You cannot unfollow yourself!', 'danger')
            return redirect(url_for('profile', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You have unfollowed {username}.', 'success')
        return redirect(url_for('profile', username=username))

    @app.route('/like/<int:tweet_id>')
    @login_required
    def like(tweet_id):
        tweet = Tweet.query.get_or_404(tweet_id)
        if tweet.has_liked(current_user):
            tweet.unlike(current_user)
            flash('Tweet unliked!', 'success')
        else:
            tweet.like(current_user)
            flash('Tweet liked!', 'success')
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/retweet/<int:tweet_id>')
    @login_required
    def retweet(tweet_id):
        tweet = Tweet.query.get_or_404(tweet_id)
        if tweet.user_id == current_user.id:
            flash('You cannot retweet your own tweet!', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        existing_retweet = Retweet.query.filter_by(user_id=current_user.id, tweet_id=tweet_id).first()
        if existing_retweet:
            db.session.delete(existing_retweet)
            flash('Retweet removed!', 'success')
        else:
            retweet = Retweet(user_id=current_user.id, tweet_id=tweet_id)
            db.session.add(retweet)
            flash('Tweet retweeted!', 'success')
        db.session.commit()
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/delete_tweet/<int:tweet_id>', methods=['GET', 'POST'])
    @login_required
    def delete_tweet(tweet_id):
        try:
            tweet = Tweet.query.get_or_404(tweet_id)
            if tweet.author != current_user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'You cannot delete this tweet.'}), 403
                flash('You cannot delete this tweet.', 'danger')
                return redirect(url_for('dashboard'))
            
            # Delete the tweet image if it exists
            if tweet.image:
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tweets', tweet.image)
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            # Delete associated likes and retweets first
            Like.query.filter_by(tweet_id=tweet.id).delete()
            Retweet.query.filter_by(tweet_id=tweet.id).delete()
            
            # Delete the tweet
            db.session.delete(tweet)
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Tweet deleted successfully!'})
                
            flash('Tweet deleted successfully!', 'success')
            return redirect(request.referrer or url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Error deleting tweet. Please try again.'}), 500
                
            flash('Error deleting tweet. Please try again.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

    # API endpoints
    @app.route('/api/tweets', methods=['GET'])
    def get_tweets():
        tweets = Tweet.query.order_by(Tweet.created_at.desc()).all()
        return jsonify([{
            'id': tweet.id,
            'content': tweet.content,
            'user_id': tweet.user_id,
            'username': tweet.author.username,
            'created_at': tweet.created_at.isoformat(),
            'likes': tweet.likes.count(),
            'retweets': tweet.retweets.count()
        } for tweet in tweets])

    @app.route('/api/tweets', methods=['POST'])
    @login_required
    def create_tweet():
        data = request.json
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        tweet = Tweet(content=data['content'], user_id=current_user.id)
        db.session.add(tweet)
        db.session.commit()
        return jsonify({
            'id': tweet.id,
            'content': tweet.content,
            'user_id': tweet.user_id,
            'username': current_user.username,
            'created_at': tweet.created_at.isoformat()
        }), 201

    @app.route('/api/tweets/<int:tweet_id>/like', methods=['POST'])
    @login_required
    def api_like_tweet(tweet_id):
        tweet = Tweet.query.get_or_404(tweet_id)
        if tweet.has_liked(current_user):
            tweet.unlike(current_user)
            return jsonify({'message': 'Tweet unliked'})
        else:
            tweet.like(current_user)
            return jsonify({'message': 'Tweet liked'})

    @app.route('/api/tweets/<int:tweet_id>/retweet', methods=['POST'])
    @login_required
    def api_retweet(tweet_id):
        tweet = Tweet.query.get_or_404(tweet_id)
        if tweet.user_id == current_user.id:
            return jsonify({'error': 'You cannot retweet your own tweet'}), 400
        existing_retweet = Retweet.query.filter_by(user_id=current_user.id, tweet_id=tweet_id).first()
        if existing_retweet:
            db.session.delete(existing_retweet)
            message = 'Retweet removed'
        else:
            retweet = Retweet(user_id=current_user.id, tweet_id=tweet_id)
            db.session.add(retweet)
            message = 'Tweet retweeted'
        db.session.commit()
        return jsonify({'message': message})

    @app.route('/api/like/<int:tweet_id>', methods=['POST'])
    @login_required
    def like_tweet(tweet_id):
        try:
            tweet = Tweet.query.get_or_404(tweet_id)
            if tweet.has_liked(current_user):
                tweet.unlike(current_user)
                db.session.commit()
                return jsonify({'success': True, 'likes_count': tweet.likes.count(), 'action': 'unliked'})
            else:
                tweet.like(current_user)
                db.session.commit()
                return jsonify({'success': True, 'likes_count': tweet.likes.count(), 'action': 'liked'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/retweet/<int:tweet_id>', methods=['POST'])
    @login_required
    def retweet_tweet(tweet_id):
        try:
            tweet = Tweet.query.get_or_404(tweet_id)
            existing_retweet = Retweet.query.filter_by(user_id=current_user.id, tweet_id=tweet_id).first()
            
            if existing_retweet:
                db.session.delete(existing_retweet)
                db.session.commit()
                return jsonify({'success': True, 'retweets_count': tweet.retweets.count(), 'action': 'unretweeted'})
            else:
                retweet = Retweet(user_id=current_user.id, tweet_id=tweet_id)
                db.session.add(retweet)
                db.session.commit()
                return jsonify({'success': True, 'retweets_count': tweet.retweets.count(), 'action': 'retweeted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/follow/<int:user_id>', methods=['POST'])
    @login_required
    def follow_user(user_id):
        user = User.query.get_or_404(user_id)
        if user == current_user:
            return jsonify({'success': False, 'message': 'You cannot follow yourself'}), 400
        if user in current_user.following:
            current_user.following.remove(user)
        else:
            current_user.following.append(user)
        db.session.commit()
        return jsonify({'success': True})

    # Add CSRF token to all responses
    @app.after_request
    def after_request(response):
        if 'text/html' in response.headers.get('Content-Type', ''):
            response.set_cookie('csrf_token', generate_csrf())
        return response

# if __name__ == '__main__':
#     app.run(debug=True)
